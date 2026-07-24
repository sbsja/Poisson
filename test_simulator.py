"""Unit tests for the layered scenario simulator (episode semantics)."""

import math
import pickle
import random

import numpy as np
import pytest

from simulator import (KNOWN_RARITIES, LAYER_DEFINITIONS, RARITIES, SEED_KEYS,
                       ConfigError, ScenarioSimulator, SimConfig,
                       UnknownCombinationClassifier, assign_rarity_counts,
                       compute_unknown_weight, compute_window_stats,
                       episode_transition_action)

_STREET_ELEMENTS = [
    {"name": "constant_lane", "probability": 0.493},
    {"name": "forced_merge_proceeding", "probability": 0.169},
    {"name": "road_split_proceeding", "probability": 0.079},
    {"name": "lane_split_proceeding", "probability": 0.072},
    {"name": "added_lane_proceeding", "probability": 0.034},
    {"name": "road_split_exiting", "probability": 0.014},
    {"name": "lane_split_exiting", "probability": 0.013},
    {"name": "removed_lane", "probability": 0.012},
    {"name": "forced_merge_merging", "probability": 0.010},
    {"name": "added_lane_merging", "probability": 0.006},
    {"name": "added_lane", "probability": 0.003},
    {"name": "overlap_zone", "probability": 0.095},
]

_SEEDS = {"element_count": 12345, "rarity_assignment": 23456,
          "transition_matrix": 34567, "duration": 45678,
          "initial_state": 56789, "transition_sampling": 67890,
          "pattern_rules": 78901}


def _layers(**over):
    base = {
        "street": {"mean_duration": 300.0, "variance_duration": 20000.0,
                   "allow_unknown": False,
                   "fixed_elements": [dict(e) for e in _STREET_ELEMENTS]},
        "temporal_modifications": {"mean_duration": 600.0,
                                   "variance_duration": 90000.0,
                                   "element_count_min": 30,
                                   "element_count_max": 46,
                                   "allow_unknown": True},
        "ego_maneuver": {"mean_duration": 30.0, "variance_duration": 400.0,
                         "element_count_min": 7, "element_count_max": 12,
                         "allow_unknown": True},
        "ru_maneuver": {"mean_duration": 45.0, "variance_duration": 900.0,
                        "element_count_min": 7, "element_count_max": 12,
                        "allow_unknown": True},
        "environmental_conditions": {"mean_duration": 1800.0,
                                     "variance_duration": 500000.0,
                                     "element_count_min": 15,
                                     "element_count_max": 21,
                                     "allow_unknown": False},
        "triggering_conditions": {"mean_duration": 120.0,
                                  "variance_duration": 8000.0,
                                  "element_count_min": 50,
                                  "element_count_max": 100,
                                  "allow_unknown": True},
    }
    base.update(over)
    return base


def base_config(**over):
    raw = {
        "seeds": dict(_SEEDS),
        "global_seed": 42,
        "target_total_miles": 50.0,
        "average_speed_mph": 50.0,
        "min_duration_seconds": 1.0,
        "mileage_window_miles": 10.0,
        "enable_unknown_combinations": True,
        "enable_hash_combinations": False,
        "enable_hidden_triggering_unknowns": True,
        "full_scenario_unknowns": {
            "enabled": True, "target_stationary_mass": 0.004,
            "calibration_samples": 200_000, "calibration_seed": 90123},
        "combination_rules": {
            "manual": [{"street": "forced_merge_merging",
                        "environmental_conditions": "environment_000"}],
            "generated_max_rules": 12,
            "generated_layers_per_rule": 2,
            "generated_target_mass": 0.005,
        },
        "rarity_proportions": {"common": 0.50, "medium": 0.25, "rare": 0.10,
                               "very_rare": 0.05, "unknown": 0.10},
        "base_weights": {"common": 1.0, "medium": 0.4, "rare": 0.1,
                         "very_rare": 0.03},
        "unknown_weight_mode": "calculated",
        "target_unknown_element_probability": 0.004,
        "fixed_unknown_weight": 0.001,
        "unknown_combination_probability": 0.005,
        "concentration_scale": 20000.0,
        "allow_self_transition": True,
        "layers": _layers(),
    }
    raw.update(over)
    return SimConfig.from_dict(raw)


def seeds_with(**over):
    s = dict(_SEEDS)
    s.update(over)
    return s


_COUNTS = {"common": 37, "medium": 19, "rare": 8, "very_rare": 4, "unknown": 7}
_UNKNOWN_LAYERS = {"temporal_modifications", "ego_maneuver", "ru_maneuver",
                   "triggering_conditions"}


# ------------------------------------------------------ episode rules (unit)

def test_episode_transition_action_rules():
    # rule 1: known -> unknown opens
    assert episode_transition_action(False, True, False) == (False, True)
    # rule 2: unknown -> known closes
    assert episode_transition_action(True, False, False) == (True, False)
    # rule 3: unknown -> different unknown restarts (close + open)
    assert episode_transition_action(True, True, False) == (True, True)
    # rule 4: self-transition on same unknown element continues
    assert episode_transition_action(True, True, True) == (False, False)
    # known -> known: nothing
    assert episode_transition_action(False, False, False) == (False, False)
    assert episode_transition_action(False, False, True) == (False, False)


# ------------------------------------------------------------- hash classifier
# (mechanism currently disabled for counting, but kept intact for later)

def _random_tuples(n, seed=0):
    rng = random.Random(seed)
    return [tuple(f"{p}_{rng.randrange(100):03d}" for _, p in LAYER_DEFINITIONS)
            for _ in range(n)]


def test_hash_classifier_deterministic_and_seeded():
    c42 = UnknownCombinationClassifier(42, 0.005)
    c43 = UnknownCombinationClassifier(43, 0.005)
    tuples = _random_tuples(20000)
    r42 = [c42.is_unknown_combination(t) for t in tuples]
    r43 = [c43.is_unknown_combination(t) for t in tuples]
    assert 0.003 < sum(r42) / len(r42) < 0.007
    assert r42 != r43
    assert r42 == [c42.is_unknown_combination(t) for t in tuples]


def test_combination_rule_validation():
    # a rule must span at least two layers
    with pytest.raises(ConfigError):
        base_config(combination_rules={
            "manual": [{"street": "constant_lane"}]})
    # unknown layer key
    with pytest.raises(ConfigError):
        base_config(combination_rules={
            "manual": [{"street": "constant_lane", "weather": "x"}]})
    # nonexistent element name is rejected when the simulator is built
    cfg = base_config(combination_rules={
        "manual": [{"street": "no_such_element",
                    "environmental_conditions": "environment_000"}]})
    with pytest.raises(ConfigError):
        ScenarioSimulator(cfg)


def test_combination_rule_rejects_unknown_rarity_elements():
    # find an unknown-rarity element in a sampled layer, reference it in a
    # rule -> must be rejected (combinations are known-element interactions)
    sim = ScenarioSimulator(base_config())
    ego = sim.layers[2]
    unk_name = ego.names[ego.is_unknown.index(True)]
    cfg = base_config(combination_rules={
        "manual": [{"ego_maneuver": unk_name, "street": "constant_lane"}]})
    with pytest.raises(ConfigError) as ei:
        ScenarioSimulator(cfg)
    assert "unknown-rarity" in str(ei.value)


def test_generated_rules_reproducible_and_calibrated():
    s1 = ScenarioSimulator(base_config())
    s2 = ScenarioSimulator(base_config())
    assert [r.description for r in s1.rules] == \
           [r.description for r in s2.rules]
    gen = [r for r in s1.rules if r.source == "generated"]
    assert gen, "expected generated rules"
    for r in s1.rules:
        assert len(r.items) >= 2
        assert 0 < r.mass < 1
    # generation stops once the target mass is reached (last rule may overshoot)
    gen_mass = sum(r.mass for r in gen)
    assert gen_mass >= 0.005 or len(gen) == 12
    # different pattern seed -> different rules, identical layers
    s3 = ScenarioSimulator(base_config(seeds=seeds_with(pattern_rules=999)))
    assert [r.description for r in s3.rules if r.source == "generated"] != \
           [r.description for r in gen]
    assert all(a.names == b.names for a, b in zip(s1.layers, s3.layers))


# --------------------------------------------------------------- rarity/weights

def test_rarity_counts_sum_and_proportions():
    props = base_config().rarity_proportions
    for n in range(7, 101):
        counts = assign_rarity_counts(n, props)
        assert sum(counts.values()) == n
        for r in RARITIES:
            assert abs(counts[r] - n * props[r]) < 1.0


def test_calculated_unknown_weight_formula_and_target():
    cfg = base_config()
    w = compute_unknown_weight(_COUNTS, cfg)
    known_mass = sum(_COUNTS[r] * cfg.base_weights[r] for r in KNOWN_RARITIES)
    assert math.isclose(w, 0.004 * known_mass / (7 * 0.996), rel_tol=1e-12)
    total = known_mass + 7 * w
    assert math.isclose(7 * w / total, 0.004, rel_tol=1e-9)
    assert w < cfg.base_weights["very_rare"]


def test_calculated_unknown_weight_error_lists_remedies():
    cfg = base_config()
    cfg.target_unknown_element_probability = 0.5   # after validation, direct
    with pytest.raises(ConfigError) as ei:
        compute_unknown_weight(_COUNTS, cfg)
    msg = str(ei.value)
    assert "proportion of unknown elements" in msg and "fixed" in msg
    # and an infeasible target is rejected already at config validation
    with pytest.raises(ConfigError):
        base_config(target_unknown_element_probability=0.5)


def test_fixed_mode_uses_and_validates_fixed_weight():
    cfg = base_config(unknown_weight_mode="fixed")
    assert compute_unknown_weight(_COUNTS, cfg) == 0.001
    with pytest.raises(ConfigError):
        compute_unknown_weight(
            _COUNTS, base_config(unknown_weight_mode="fixed",
                                 fixed_unknown_weight=0.05))


# ------------------------------------------------------------------ validation

def test_seeds_validated():
    with pytest.raises(ConfigError):
        base_config(seeds={"element_count": 1})
    with pytest.raises(ConfigError):
        base_config(seeds=seeds_with(bogus=7))
    assert set(base_config().seeds) == set(SEED_KEYS)


def test_fixed_elements_validated():
    bad = _layers()
    bad["street"]["fixed_elements"][0]["probability"] = 0.9   # sum != 1
    with pytest.raises(ConfigError):
        base_config(layers=bad)
    bad2 = _layers()
    bad2["street"]["allow_unknown"] = True   # fixed layers are all-known
    with pytest.raises(ConfigError):
        base_config(layers=bad2)


def test_too_small_range_for_unknowns_rejected():
    bad = _layers()
    bad["ego_maneuver"]["element_count_min"] = 4   # yields 0 unknown elements
    bad["ego_maneuver"]["element_count_max"] = 5
    with pytest.raises(ConfigError):
        base_config(layers=bad)


def test_infeasible_range_rejected_with_clear_error():
    bad = _layers()
    bad["ego_maneuver"]["element_count_max"] = 14   # n=13,14 infeasible
    with pytest.raises(ConfigError) as ei:
        base_config(layers=bad)
    assert "infeasible" in str(ei.value)


def test_invalid_proportions_rejected():
    bad = {"common": 0.9, "medium": 0.05, "rare": 0.03, "very_rare": 0.01,
           "unknown": 0.05}
    with pytest.raises(ConfigError):
        base_config(rarity_proportions=bad)


# ------------------------------------------------------------ layer construction

def test_street_layer_fixed_and_exact():
    sim = ScenarioSimulator(base_config())
    street = sim.layers[0]
    assert street.is_fixed and street.n_elements == 12
    assert not any(street.is_unknown)                 # no unknown elements
    assert street.unknown_weight is None
    expected = np.array([e["probability"] for e in _STREET_ELEMENTS])
    assert np.allclose(street.transition_probs, expected, atol=1e-12)
    assert np.allclose(street.initial_probs, expected, atol=1e-12)
    assert street.names[0] == "constant_lane"


def test_street_vector_not_dirichlet_perturbed():
    # changing the transition_matrix seed must NOT change the street vector,
    # but must change the sampled layers' vectors
    s1 = ScenarioSimulator(base_config())
    s2 = ScenarioSimulator(base_config(seeds=seeds_with(transition_matrix=999)))
    assert np.array_equal(s1.layers[0].transition_probs,
                          s2.layers[0].transition_probs)
    assert any(not np.array_equal(a.transition_probs, b.transition_probs)
               for a, b in zip(s1.layers[1:], s2.layers[1:]))


def test_environment_layer_has_no_unknowns():
    sim = ScenarioSimulator(base_config())
    env = sim.layers[4]
    assert not env.is_fixed
    assert 15 <= env.n_elements <= 21
    assert not any(env.is_unknown)
    assert env.counts["unknown"] == 0
    # renormalized known proportions still sum to 1
    lp = base_config().layers["environmental_conditions"]
    props = base_config().effective_proportions(lp)
    assert math.isclose(sum(props.values()), 1.0, rel_tol=1e-12)
    assert props["unknown"] == 0.0


def test_sampled_layers_built_to_spec():
    sim = ScenarioSimulator(base_config())
    ranges = {"temporal_modifications": (30, 46), "ego_maneuver": (7, 12),
              "ru_maneuver": (7, 12), "environmental_conditions": (15, 21),
              "triggering_conditions": (50, 100)}
    for layer in sim.layers[1:]:
        lo, hi = ranges[layer.key]
        assert lo <= layer.n_elements <= hi
        assert sum(layer.counts.values()) == layer.n_elements
        assert math.isclose(float(layer.transition_probs.sum()), 1.0,
                            abs_tol=1e-9)
        if layer.key in _UNKNOWN_LAYERS:
            assert layer.counts["unknown"] >= 1
            assert layer.unknown_weight < 0.03
            assert math.isclose(layer.designed_unknown_mass(), 0.004,
                                rel_tol=1e-9)


def test_transition_vectors_permanent():
    s1 = ScenarioSimulator(base_config())
    before = [l.transition_probs.copy() for l in s1.layers]
    s1.run()
    for b, layer in zip(before, s1.layers):
        assert np.array_equal(b, layer.transition_probs)


def test_seed_streams_isolated():
    ref = ScenarioSimulator(base_config())
    s_dur = ScenarioSimulator(base_config(seeds=seeds_with(duration=999)))
    for a, b in zip(ref.layers, s_dur.layers):
        assert a.names == b.names and a.rarities == b.rarities
        assert np.array_equal(a.transition_probs, b.transition_probs)
    s_cnt = ScenarioSimulator(base_config(seeds=seeds_with(element_count=999)))
    assert s_cnt.layers[0].n_elements == 12         # street unaffected
    assert [l.n_elements for l in ref.layers[1:]] != \
           [l.n_elements for l in s_cnt.layers[1:]]


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
    rng = random.Random(9)
    ds = [sim.layers[2].sample_duration(rng, 25.0) for _ in range(20000)]
    assert min(ds) >= 25.0


def test_no_self_transition_when_disabled():
    sim = ScenarioSimulator(base_config(allow_self_transition=False))
    rng = random.Random(3)
    for _ in range(20000):
        assert sim.layers[0].sample_next_index(rng, 0, False) != 0


# ----------------------------------------------------------- episode semantics

def _run(miles=5000.0, **over):
    return ScenarioSimulator(base_config(target_total_miles=miles,
                                         **over)).run()


def test_episodes_only_from_unknown_bearing_layers():
    res = _run()
    elem = [e for e in res.episodes if e.type == "element"]
    assert len(elem) > 0
    for e in elem:
        assert e.layer in _UNKNOWN_LAYERS - {"triggering_conditions"}
    by_layer = {st["layer"]: st["episodes"] for st in res.layer_stats}
    assert by_layer["street"] == 0
    assert by_layer["environmental_conditions"] == 0
    assert sum(by_layer.values()) == len(elem)
    for e in res.episodes:
        if e.type == "full_scenario":
            assert e.layer == "scenario"
        elif e.type == "hidden_triggering_unknown":
            assert e.layer == "triggering_conditions"
            assert e.element == "hidden_triggering_unknown"
        elif e.type != "element":
            assert e.layer == "combination"


def test_triggering_unknowns_use_the_dedicated_hidden_category():
    res = _run(miles=20_000.0)
    hidden = [e for e in res.episodes
              if e.type == "hidden_triggering_unknown"]
    assert hidden
    assert not any(e.type == "element" and e.layer == "triggering_conditions"
                   for e in res.episodes)
    assert res.hidden_triggering_stats["episodes"] == len(hidden)


def test_episode_elements_are_unknown_rarity():
    res = _run()
    sim_layers = {st["layer"]: st for st in res.layer_stats}
    for e in res.episodes:
        if e.type != "element":
            continue
        st = sim_layers[e.layer]
        assert e.element in st["element_names"]
        assert st["counts"]["unknown"] >= 1


def test_episode_intervals_valid_and_per_layer_non_overlapping():
    res = _run()
    per_layer = {}
    for e in res.episodes:
        assert e.end_time_seconds is not None      # all closed at the end
        assert e.end_time_seconds >= e.start_time_seconds
        assert e.end_mileage >= e.start_mileage
        assert math.isclose(
            e.duration_miles,
            res.config.average_speed_mph * e.duration_seconds / 3600.0,
            rel_tol=1e-9, abs_tol=1e-9)
        if not e.truncated and e.type == "element":
            # combination episodes may be shorter: events in OTHER layers
            # can end them after arbitrarily small staggered gaps
            assert e.duration_seconds >= res.config.min_duration_seconds - 1e-9
        slot = (e.type, e.layer if e.type == "element" else e.element)
        per_layer.setdefault(slot, []).append(e)
    for eps in per_layer.values():
        eps.sort(key=lambda e: e.start_time_seconds)
        for a, b in zip(eps, eps[1:]):
            assert b.start_time_seconds >= a.end_time_seconds - 1e-9


def test_starts_are_ordered_and_union_bounded():
    res = _run()
    starts = [e.start_time_seconds for e in res.episodes]
    assert starts == sorted(starts)
    total_dur = sum(e.duration_seconds for e in res.episodes)
    assert res.total_unknown_time_seconds <= total_dur + 1e-6   # overlaps merge
    assert res.total_unknown_time_seconds <= res.total_time_seconds
    if res.episodes:
        assert res.total_unknown_time_seconds >= max(
            e.duration_seconds for e in res.episodes) - 1e-6


def test_episode_count_matches_unknown_entries_without_self_transitions():
    # with self-transitions disabled every transition changes the element,
    # so episodes == unknown-element selections + initial unknown layers
    res = _run(miles=3000.0, allow_self_transition=False)
    elem = [e for e in res.episodes if e.type == "element"]
    initial = sum(1 for e in elem if e.start_time_seconds == 0.0)
    selected = sum(st["unknown_selected"] for st in res.layer_stats
                   if st["layer"] != "triggering_conditions")
    assert len(elem) == selected + initial


def test_other_layer_changes_do_not_end_episodes():
    # episode durations must equal the element sojourn time of their own
    # layer; ego transitions every ~30 s, so temporal episodes must
    # frequently span multiple ego changes without being cut
    res = _run(miles=20000.0)
    long_eps = [e for e in res.episodes
                if e.type == "element"
                and e.layer == "temporal_modifications"
                and not e.truncated]
    if long_eps:   # statistically ~always present at 20k miles
        assert max(e.duration_seconds for e in long_eps) > 60.0


def test_hash_episodes_gated_by_element_unknowns():
    """A hash episode never starts while an element episode is running."""
    res = _run(miles=20000.0, enable_hash_combinations=True)
    elem = [(e.start_time_seconds, e.end_time_seconds)
            for e in res.episodes if e.type == "element"]
    for h in res.episodes:
        if h.type != "hash_combination":
            continue
        for s, t_end in elem:
            assert not (s <= h.start_time_seconds < t_end)


def test_pattern_episode_counts_match_rule_stats():
    res = _run(miles=20000.0)
    cs = res.combination_stats
    assert cs["enabled"]
    n_pattern = sum(1 for e in res.episodes if e.type == "pattern")
    assert n_pattern == cs["pattern_episodes"] == \
           sum(r["episodes"] for r in cs["rules"])
    n_hash = sum(1 for e in res.episodes if e.type == "hash_combination")
    assert n_hash == cs["hash_episodes"]
    assert n_hash == 0
    assert cs["hash_enabled"] is False


def test_hash_combinations_are_not_instantiated_or_evaluated_by_default():
    sim = ScenarioSimulator(base_config(target_total_miles=20000.0))
    assert sim.classifier is None
    res = sim.run()
    assert not any(e.type == "hash_combination" for e in res.episodes)
    assert res.combination_stats["hash_episodes"] == 0
    assert res.combination_stats["hash_enabled"] is False


def test_combinations_can_be_disabled():
    res = _run(miles=2000.0, enable_unknown_combinations=False,
               full_scenario_unknowns={"enabled": False},
               enable_hidden_triggering_unknowns=False)
    assert all(e.type == "element" for e in res.episodes)
    assert res.combination_stats["enabled"] is False


def test_truncated_episodes_flagged_at_end():
    res = _run()
    for e in res.episodes:
        if e.truncated:
            assert math.isclose(e.end_time_seconds, res.total_time_seconds,
                                rel_tol=1e-12)


# ------------------------------------------------------------ output statistics

def test_window_stats_counts_mean_variance_dispersion():
    ws = compute_window_stats([5.0, 15.0, 25.0, 25.5, 999.0],
                              total_miles=40.0, window_miles=10.0)
    assert ws["n_windows"] == 4
    assert ws["counts"] == [1, 1, 2, 0]
    assert math.isclose(ws["mean_count"], 1.0)
    assert math.isclose(ws["variance_count"], 2.0 / 3.0)
    assert math.isclose(ws["dispersion_index"], 2.0 / 3.0)


def test_inter_arrivals_consistent_and_windows_on_starts():
    res = _run(miles=2000.0, mileage_window_miles=100.0)
    inter_mi = res.inter_arrival_miles()
    inter_s = res.inter_arrival_seconds()
    assert len(inter_mi) == len(inter_s) == len(res.episodes)
    for dmi, ds in zip(inter_mi, inter_s):
        assert dmi >= 0 and ds >= 0
        assert math.isclose(dmi, res.config.average_speed_mph * ds / 3600.0,
                            rel_tol=1e-9, abs_tol=1e-9)
    ws = res.window_stats()
    assert ws["n_windows"] == int(res.total_miles // 100.0)
    assert sum(ws["counts"]) <= len(res.episodes)


# ------------------------------------------------------------------ simulation

def test_simulation_reaches_target_and_time_consistent():
    cfg = base_config(target_total_miles=25.0)
    res = ScenarioSimulator(cfg).run()
    assert res.total_miles >= 25.0
    assert math.isclose(res.total_miles,
                        cfg.average_speed_mph * res.total_time_seconds / 3600.0,
                        rel_tol=1e-9)


def test_simulation_reproducible_with_same_seeds():
    def key(res):
        return [(e.type, e.layer, e.element, e.start_mileage, e.end_mileage,
                 e.truncated) for e in res.episodes]
    r1 = ScenarioSimulator(base_config(target_total_miles=500.0)).run()
    r2 = ScenarioSimulator(base_config(target_total_miles=500.0)).run()
    assert r1.total_events == r2.total_events
    assert r1.total_time_seconds == r2.total_time_seconds
    assert key(r1) == key(r2)


def test_chunked_resume_bit_identical():
    kw = dict(target_total_miles=2000.0)
    full = ScenarioSimulator(base_config(**kw)).run()
    sim = ScenarioSimulator(base_config(**kw))
    result, state = None, None
    for _ in range(10000):
        result, state = sim.run_resumable(state, wall_limit_seconds=0.001)
        if result is not None:
            break
        sim, state = pickle.loads(pickle.dumps((sim, state)))
    assert result is not None
    assert result.total_events == full.total_events
    assert [(e.type, e.layer, e.element, e.start_mileage, e.end_mileage)
            for e in result.episodes] == \
           [(e.type, e.layer, e.element, e.start_mileage, e.end_mileage)
            for e in full.episodes]


# ------------------------------------------------------ full-scenario rarity

def _fs(**over):
    d = {"enabled": True, "target_stationary_mass": 0.004,
         "calibration_samples": 200_000, "calibration_seed": 90123}
    d.update(over)
    return d


def test_full_scenario_config_validated():
    with pytest.raises(ConfigError):
        base_config(full_scenario_unknowns=_fs(target_stationary_mass=0.0))
    with pytest.raises(ConfigError):
        base_config(full_scenario_unknowns=_fs(target_stationary_mass=1.0))
    with pytest.raises(ConfigError):
        base_config(full_scenario_unknowns=_fs(calibration_samples=5000))
    with pytest.raises(ConfigError):
        base_config(full_scenario_unknowns=_fs(calibration_seed="abc"))
    with pytest.raises(ConfigError):
        base_config(full_scenario_unknowns=_fs(bogus=1))
    with pytest.raises(ConfigError):
        base_config(enable_hidden_triggering_unknowns="yes")


def test_full_scenario_threshold_reproducible():
    s1 = ScenarioSimulator(base_config())
    s2 = ScenarioSimulator(base_config())
    assert s1.full_scenario.calibrated_rarity_threshold == \
           s2.full_scenario.calibrated_rarity_threshold
    assert s1.full_scenario.achieved_sampled_mass == \
           s2.full_scenario.achieved_sampled_mass
    s3 = ScenarioSimulator(base_config(
        full_scenario_unknowns=_fs(calibration_seed=555)))
    assert s3.full_scenario.calibrated_rarity_threshold != \
           s1.full_scenario.calibrated_rarity_threshold
    # calibration must not touch the other streams: layers identical
    assert all(a.names == b.names for a, b in zip(s1.layers, s3.layers))


def test_full_scenario_calibration_mass_within_tolerance():
    clf = ScenarioSimulator(base_config()).full_scenario
    n = clf.calibration_samples
    # in-sample achieved mass matches the target up to quantile rounding
    assert abs(clf.achieved_sampled_mass
               - clf.target_stationary_mass) <= 3.0 / n
    assert clf.eligible_sampled_mass > clf.target_stationary_mass


def test_no_hash_or_pattern_episodes_with_full_scenario():
    res = _run(miles=5000.0, enable_unknown_combinations=False)
    types = {e.type for e in res.episodes}
    assert types <= {"element", "hidden_triggering_unknown", "full_scenario"}
    assert res.combination_stats["hash_episodes"] == 0
    assert res.combination_stats["pattern_episodes"] == 0
    assert res.full_scenario_stats["enabled"] is True
    assert res.full_scenario_stats["episodes"] == \
           sum(1 for e in res.episodes if e.type == "full_scenario")


def test_full_scenario_classification_uses_all_six_layers():
    sim = ScenarioSimulator(base_config())
    idx = tuple(0 for _ in range(6))
    p = sim.tuple_probability(idx)
    expected = 1.0
    for k in range(6):
        expected *= float(sim.layers[k].transition_probs[0])
    assert math.isclose(p, expected, rel_tol=1e-12)
    # changing any single coordinate changes the probability
    for k in range(6):
        alt = list(idx)
        alt[k] = 1
        q0 = float(sim.layers[k].transition_probs[0])
        q1 = float(sim.layers[k].transition_probs[1])
        if q0 != q1:      # true for continuous Dirichlet / distinct fixed probs
            assert sim.tuple_probability(tuple(alt)) != p

    # Unknown elements belong to element/hidden-trigger routes, not the
    # all-known full-scenario route.
    for k, layer in enumerate(sim.layers):
        unknown = next((i for i, value in enumerate(layer.is_unknown)
                        if value), None)
        if unknown is not None:
            alt = list(idx)
            alt[k] = unknown
            assert sim.is_rare_tuple(tuple(alt)) is False
            break


def test_full_scenario_rare_to_rare_and_self_transition_continuity():
    # elevated target -> rare tuples are common enough that back-to-back
    # rare A -> rare B transitions occur; self-transitions must never split
    res = _run(miles=3000.0,
               full_scenario_unknowns=_fs(target_stationary_mass=0.25))
    full = sorted((e for e in res.episodes if e.type == "full_scenario"),
                  key=lambda e: e.start_time_seconds)
    assert len(full) > 50
    back_to_back = 0
    for a, b in zip(full, full[1:]):
        assert b.start_time_seconds >= a.end_time_seconds - 1e-9
        if abs(b.start_time_seconds - a.end_time_seconds) < 1e-9:
            back_to_back += 1
            # rare A -> rare B: the exact scenario must differ; an unchanged
            # tuple (self-transition) must never split an episode
            assert a.element != b.element
    assert back_to_back > 0
    for e in full:
        assert e.layer == "scenario"
        assert len(e.element.split("|")) == 6


def test_union_time_with_overlapping_element_and_full_episodes():
    res = _run(miles=3000.0,
               full_scenario_unknowns=_fs(target_stationary_mass=0.25))
    # independent interval-merge over ALL episodes must equal the union
    ivs = sorted((e.start_time_seconds, e.end_time_seconds)
                 for e in res.episodes)
    merged = 0.0
    cur_s, cur_e = None, None
    for s, t_end in ivs:
        if cur_s is None:
            cur_s, cur_e = s, t_end
        elif s <= cur_e + 1e-12:
            cur_e = max(cur_e, t_end)
        else:
            merged += cur_e - cur_s
            cur_s, cur_e = s, t_end
    if cur_s is not None:
        merged += cur_e - cur_s
    assert math.isclose(merged, res.total_unknown_time_seconds,
                        rel_tol=1e-9, abs_tol=1e-6)
    # overlaps must exist at this target so the test is meaningful
    total = sum(e.duration_seconds for e in res.episodes)
    assert total > res.total_unknown_time_seconds
