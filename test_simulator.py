"""Unit tests for the layered scenario simulator (pytest)."""

import math
import pickle
import random

import numpy as np
import pytest

from simulator import (KNOWN_RARITIES, LAYER_DEFINITIONS, RARITIES, SEED_KEYS,
                       ConfigError, ScenarioSimulator, SimConfig,
                       UnknownCombinationClassifier, assign_rarity_counts,
                       compute_unknown_weight, compute_window_stats)

_LAYER_DURATIONS = {
    "street": (300.0, 20000.0),
    "temporal_modifications": (600.0, 90000.0),
    "ego_maneuver": (30.0, 400.0),
    "ru_maneuver": (45.0, 900.0),
    "environmental_conditions": (1800.0, 500000.0),
    "triggering_conditions": (120.0, 8000.0),
}

_SEEDS = {"element_count": 12345, "rarity_assignment": 23456,
          "transition_matrix": 34567, "duration": 45678,
          "initial_state": 56789, "transition_sampling": 67890}


def base_config(**over):
    raw = {
        "seeds": dict(_SEEDS),
        "global_seed": 42,
        "target_total_miles": 50.0,
        "average_speed_mph": 50.0,
        "min_duration_seconds": 1.0,
        "count_initial_scenario": True,
        "mileage_window_miles": 10.0,
        "element_count_min": 50,
        "element_count_max": 100,
        "rarity_proportions": {"common": 0.50, "medium": 0.25, "rare": 0.10,
                               "very_rare": 0.05, "unknown": 0.10},
        "base_weights": {"common": 1.0, "medium": 0.4, "rare": 0.1,
                         "very_rare": 0.03},
        "unknown_weight_mode": "calculated",
        "target_unknown_element_probability": 0.004,
        "fixed_unknown_weight": 0.001,
        "unknown_combination_probability": 0.005,
        "concentration_scale": 100.0,
        "allow_self_transition": True,
        "layers": {k: {"mean_duration": m, "variance_duration": v}
                   for k, (m, v) in _LAYER_DURATIONS.items()},
    }
    raw.update(over)
    return SimConfig.from_dict(raw)


def seeds_with(**over):
    s = dict(_SEEDS)
    s.update(over)
    return s


_COUNTS = {"common": 37, "medium": 19, "rare": 8, "very_rare": 4, "unknown": 7}


# ------------------------------------------------------------- hash classifier

def _random_tuples(n, seed=0):
    rng = random.Random(seed)
    return [tuple(f"{p}_{rng.randrange(100):03d}" for _, p in LAYER_DEFINITIONS)
            for _ in range(n)]


def test_hash_classifier_deterministic():
    c = UnknownCombinationClassifier(42, 0.005)
    t = ("street_012", "temporal_004", "ego_031", "ru_008",
         "environment_022", "trigger_003")
    v1, v2 = c.hash_value(t), c.hash_value(t)
    assert v1 == v2
    assert 0.0 <= v1 < 1.0
    assert c.is_unknown_combination(t) == c.is_unknown_combination(t)


def test_hash_classifier_rate_and_seed_dependence():
    c42 = UnknownCombinationClassifier(42, 0.005)
    c43 = UnknownCombinationClassifier(43, 0.005)
    tuples = _random_tuples(20000)
    r42 = [c42.is_unknown_combination(t) for t in tuples]
    r43 = [c43.is_unknown_combination(t) for t in tuples]
    rate42 = sum(r42) / len(r42)
    rate43 = sum(r43) / len(r43)
    assert 0.003 < rate42 < 0.007          # ~0.5% +- 4 sigma
    assert 0.003 < rate43 < 0.007
    assert r42 != r43                       # different seed -> different set
    assert r42 == [c42.is_unknown_combination(t) for t in tuples]  # stable


def test_hash_classifier_no_storage():
    c = UnknownCombinationClassifier(42, 0.005)
    for t in _random_tuples(1000, seed=1):
        c.is_unknown_combination(t)
    assert not any(isinstance(v, (dict, set, list)) and len(v) > 10
                   for v in vars(c).values())  # nothing enumerated/stored


# --------------------------------------------------------------- rarity counts

def test_rarity_counts_sum_and_proportions():
    props = base_config().rarity_proportions
    for n in range(50, 101):
        counts = assign_rarity_counts(n, props)
        assert sum(counts.values()) == n
        for r in RARITIES:
            assert abs(counts[r] - n * props[r]) < 1.0  # largest remainder


# -------------------------------------------------------------- unknown weight

def test_calculated_unknown_weight_formula_and_target():
    cfg = base_config()
    w = compute_unknown_weight(_COUNTS, cfg)
    known_mass = sum(_COUNTS[r] * cfg.base_weights[r] for r in KNOWN_RARITIES)
    expected = 0.004 * known_mass / (_COUNTS["unknown"] * (1 - 0.004))
    assert math.isclose(w, expected, rel_tol=1e-12)
    # resulting unknown probability mass hits the target exactly
    total = known_mass + _COUNTS["unknown"] * w
    assert math.isclose(_COUNTS["unknown"] * w / total, 0.004, rel_tol=1e-9)
    assert w < cfg.base_weights["very_rare"]


def test_calculated_unknown_weight_error_lists_remedies():
    cfg = base_config(target_unknown_element_probability=0.5)
    with pytest.raises(ConfigError) as ei:
        compute_unknown_weight(_COUNTS, cfg)
    msg = str(ei.value)
    assert "proportion of unknown elements" in msg
    assert "target_unknown_element_probability" in msg
    assert "fixed" in msg


def test_fixed_mode_uses_and_validates_fixed_weight():
    cfg = base_config(unknown_weight_mode="fixed")
    assert compute_unknown_weight(_COUNTS, cfg) == 0.001
    cfg_bad = base_config(unknown_weight_mode="fixed", fixed_unknown_weight=0.05)
    with pytest.raises(ConfigError):
        compute_unknown_weight(_COUNTS, cfg_bad)  # not < very_rare weight


def test_calculated_mode_requires_unknown_elements():
    cfg = base_config()
    counts = dict(_COUNTS, unknown=0)
    with pytest.raises(ConfigError):
        compute_unknown_weight(counts, cfg)


# ------------------------------------------------------------------ validation

def test_invalid_proportions_rejected():
    bad = {"common": 0.9, "medium": 0.05, "rare": 0.03, "very_rare": 0.01,
           "unknown": 0.05}  # sums to 1.04
    with pytest.raises(ConfigError):
        base_config(rarity_proportions=bad)


def test_invalid_mode_rejected():
    with pytest.raises(ConfigError):
        base_config(unknown_weight_mode="banana")


def test_unknown_base_weight_rejected():
    bw = {"common": 1.0, "medium": 0.4, "rare": 0.1, "very_rare": 0.03,
          "unknown": 0.5}
    with pytest.raises(ConfigError):
        base_config(base_weights=bw)


def test_seeds_validated():
    with pytest.raises(ConfigError):
        base_config(seeds={"element_count": 1})           # missing entries
    with pytest.raises(ConfigError):
        base_config(seeds=seeds_with(bogus=7))            # unknown entry
    with pytest.raises(ConfigError):
        base_config(seeds=seeds_with(duration="abc"))     # non-int
    assert set(base_config().seeds) == set(SEED_KEYS)


# ------------------------------------------------------------ layers / vectors

def test_layers_built_to_spec():
    sim = ScenarioSimulator(base_config())
    assert len(sim.layers) == 6
    for layer in sim.layers:
        assert 50 <= layer.n_elements <= 100
        assert sum(layer.counts.values()) == layer.n_elements
        assert len(layer.names) == len(set(layer.names))
        # unknown weight strictly smallest
        assert layer.unknown_weight < min(base_config().base_weights.values())
        # transition vector: valid probability vector, fixed size
        assert math.isclose(float(layer.transition_probs.sum()), 1.0, abs_tol=1e-9)
        assert (layer.transition_probs >= 0).all()
        assert len(layer.transition_probs) == layer.n_elements
        # designed unknown mass hits the calculated-mode target exactly
        assert math.isclose(layer.designed_unknown_mass(), 0.004, rel_tol=1e-9)


def test_transition_vectors_reproducible_and_permanent():
    s1 = ScenarioSimulator(base_config())
    s2 = ScenarioSimulator(base_config())
    for l1, l2 in zip(s1.layers, s2.layers):
        assert np.array_equal(l1.transition_probs, l2.transition_probs)
    before = [l.transition_probs.copy() for l in s1.layers]
    s1.run()  # simulation must not resample transition probabilities
    for b, layer in zip(before, s1.layers):
        assert np.array_equal(b, layer.transition_probs)


def test_no_self_transition_when_disabled():
    sim = ScenarioSimulator(base_config(allow_self_transition=False))
    layer = sim.layers[0]
    rng = random.Random(3)
    current = 5
    for _ in range(20000):
        assert layer.sample_next_index(rng, current, False) != current


# ------------------------------------------------------------ seed separation

def test_seed_streams_isolated():
    """Each seed controls exactly its own random source."""
    ref = ScenarioSimulator(base_config())

    # different duration seed: layer structure and vectors identical
    s_dur = ScenarioSimulator(base_config(seeds=seeds_with(duration=999)))
    for a, b in zip(ref.layers, s_dur.layers):
        assert a.names == b.names
        assert a.rarities == b.rarities
        assert np.array_equal(a.transition_probs, b.transition_probs)

    # different transition_matrix seed: same elements/rarities, new vectors
    s_mat = ScenarioSimulator(base_config(seeds=seeds_with(transition_matrix=999)))
    assert all(a.rarities == b.rarities for a, b in zip(ref.layers, s_mat.layers))
    assert any(not np.array_equal(a.transition_probs, b.transition_probs)
               for a, b in zip(ref.layers, s_mat.layers))

    # different rarity_assignment seed: same counts, different shuffle
    s_rar = ScenarioSimulator(base_config(seeds=seeds_with(rarity_assignment=999)))
    assert all(a.counts == b.counts for a, b in zip(ref.layers, s_rar.layers))
    assert any(a.rarities != b.rarities for a, b in zip(ref.layers, s_rar.layers))

    # different element_count seed: different element counts (overwhelmingly)
    s_cnt = ScenarioSimulator(base_config(seeds=seeds_with(element_count=999)))
    assert [l.n_elements for l in ref.layers] != \
           [l.n_elements for l in s_cnt.layers]

    # different initial_state seed: same layers, (typically) different start
    s_ini = ScenarioSimulator(base_config(seeds=seeds_with(initial_state=999)))
    assert all(a.names == b.names for a, b in zip(ref.layers, s_ini.layers))


# -------------------------------------------------------------------- durations

def test_gamma_parameterization_moments():
    mean, var = 30.0, 400.0
    shape, scale = mean ** 2 / var, var / mean
    rng = random.Random(123)
    xs = [rng.gammavariate(shape, scale) for _ in range(200000)]
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    assert abs(m - mean) / mean < 0.02
    assert abs(v - var) / var < 0.06


def test_duration_positive_and_min_clamped():
    sim = ScenarioSimulator(base_config())
    layer = sim.layers[2]  # ego, mean 30
    rng = random.Random(9)
    ds = [layer.sample_duration(rng, 25.0) for _ in range(20000)]
    assert min(ds) >= 25.0
    assert all(d > 0 for d in ds)


# --------------------------------------------------- scenario classification

def test_scenario_unknown_via_element():
    sim = ScenarioSimulator(base_config())
    k = next(i for i, l in enumerate(sim.layers) if any(l.is_unknown))
    idx = [0] * 6
    idx[k] = sim.layers[k].is_unknown.index(True)
    is_unk, reason = sim.classify_scenario(tuple(idx))
    assert is_unk and reason == "unknown_element"


def test_scenario_unknown_via_combination():
    sim = ScenarioSimulator(base_config())
    rng = random.Random(1)
    found = None
    for _ in range(200000):
        idx = tuple(rng.randrange(l.n_elements) for l in sim.layers)
        if any(l.is_unknown[i] for l, i in zip(sim.layers, idx)):
            continue
        is_unk, reason = sim.classify_scenario(idx)
        if is_unk:
            assert reason == "unknown_combination"
            found = idx
            break
    assert found is not None
    # deterministic: same tuple classifies the same way again
    assert sim.classify_scenario(found) == (True, "unknown_combination")


def test_no_double_count_same_tuple():
    sim = ScenarioSimulator(base_config())
    k = next(i for i, l in enumerate(sim.layers) if any(l.is_unknown))
    unk_idx = [0] * 6
    unk_idx[k] = sim.layers[k].is_unknown.index(True)
    unk_tuple = tuple(unk_idx)
    assert sim.classify_scenario(unk_tuple)[0] is True
    # staying in the same unknown tuple -> NOT counted again
    counted, reason = ScenarioSimulator.check_new_scenario(
        unk_tuple, unk_tuple, sim.classify_scenario)
    assert counted is False and reason is None
    # entering a different unknown tuple -> counted once
    other = list(unk_tuple)
    other[(k + 1) % 6] = (other[(k + 1) % 6] + 1) % sim.layers[(k + 1) % 6].n_elements
    counted, reason = ScenarioSimulator.check_new_scenario(
        tuple(other), unk_tuple, sim.classify_scenario)
    assert counted is True and reason == "unknown_element"


# ------------------------------------------------------------ output statistics

def test_window_stats_counts_mean_variance_dispersion():
    mileages = [5.0, 15.0, 25.0, 25.5, 999.0]  # 999 beyond complete windows
    ws = compute_window_stats(mileages, total_miles=40.0, window_miles=10.0)
    assert ws["n_windows"] == 4
    assert ws["counts"] == [1, 1, 2, 0]
    assert math.isclose(ws["mean_count"], 1.0)
    assert math.isclose(ws["variance_count"], 2.0 / 3.0)
    assert math.isclose(ws["dispersion_index"], 2.0 / 3.0)


def test_window_stats_requires_complete_window():
    with pytest.raises(ValueError):
        compute_window_stats([1.0], total_miles=5.0, window_miles=10.0)


def test_inter_arrival_times_and_distances_consistent():
    cfg = base_config(target_total_miles=2000.0)
    res = ScenarioSimulator(cfg).run()
    assert len(res.encounters) > 0
    inter_mi = res.inter_arrival_miles()
    inter_s = res.inter_arrival_seconds()
    assert len(inter_mi) == len(inter_s) == len(res.encounters)
    for dmi, ds in zip(inter_mi, inter_s):
        assert dmi >= 0 and ds >= 0
        # constant speed: distance and time gaps must be proportional
        assert math.isclose(dmi, cfg.average_speed_mph * ds / 3600.0,
                            rel_tol=1e-9, abs_tol=1e-9)
    # positions reconstruct from inter-arrivals
    assert math.isclose(sum(inter_mi), res.encounters[-1].mileage, rel_tol=1e-9)
    ws = res.window_stats()
    assert sum(ws["counts"]) <= len(res.encounters)
    assert ws["n_windows"] == int(res.total_miles // cfg.mileage_window_miles)


# ------------------------------------------------------------------ simulation

def test_simulation_reaches_target_and_time_consistent():
    cfg = base_config(target_total_miles=25.0)
    res = ScenarioSimulator(cfg).run()
    assert res.total_miles >= 25.0
    assert math.isclose(res.total_miles,
                        cfg.average_speed_mph * res.total_time_seconds / 3600.0,
                        rel_tol=1e-9)
    assert res.total_events > 0


def test_simulation_reproducible_with_same_seeds():
    """Running twice with the same config and seeds -> identical results."""
    r1 = ScenarioSimulator(base_config(target_total_miles=100.0)).run()
    r2 = ScenarioSimulator(base_config(target_total_miles=100.0)).run()
    assert r1.total_events == r2.total_events
    assert r1.total_time_seconds == r2.total_time_seconds
    assert r1.total_miles == r2.total_miles
    assert [(e.mileage, e.time_seconds, e.scenario, e.reason)
            for e in r1.encounters] == \
           [(e.mileage, e.time_seconds, e.scenario, e.reason)
            for e in r2.encounters]


def test_encounters_recorded_with_mileage_and_time():
    res = ScenarioSimulator(base_config(target_total_miles=2000.0)).run()
    prev_mile = -1.0
    for e in res.encounters:
        assert 0.0 <= e.mileage <= res.total_miles
        assert e.mileage >= prev_mile           # monotonically ordered
        assert e.reason in ("unknown_element", "unknown_combination")
        assert len(e.scenario.split("|")) == 6
        prev_mile = e.mileage
    inter = res.inter_arrival_miles()
    assert len(inter) == len(res.encounters)
    assert all(d >= 0 for d in inter)


def test_chunked_resume_bit_identical():
    """Checkpoint/resume (pickle round-trip) must reproduce a single
    uninterrupted run exactly."""
    kw = dict(target_total_miles=2000.0)
    full = ScenarioSimulator(base_config(**kw)).run()
    sim = ScenarioSimulator(base_config(**kw))
    result, state = None, None
    for _ in range(10000):
        result, state = sim.run_resumable(state, wall_limit_seconds=0.001)
        if result is not None:
            break
        sim, state = pickle.loads(pickle.dumps((sim, state)))  # checkpoint cycle
    assert result is not None
    assert result.total_events == full.total_events
    assert result.total_time_seconds == full.total_time_seconds
    assert [(e.mileage, e.scenario, e.reason) for e in result.encounters] == \
           [(e.mileage, e.scenario, e.reason) for e in full.encounters]


def test_encounter_mileage_time_consistency():
    cfg = base_config(target_total_miles=2000.0)
    res = ScenarioSimulator(cfg).run()
    for e in res.encounters:
        expected_miles = cfg.average_speed_mph * e.time_seconds / 3600.0
        assert math.isclose(e.mileage, expected_miles, rel_tol=1e-9, abs_tol=1e-9)
