"""Unit tests for the layered scenario simulator (episode semantics)."""

import copy
import math
import pickle
import random
from pathlib import Path

import numpy as np
import pytest

from simulator import (KNOWN_RARITIES, LAYER_DEFINITIONS, RARITIES, SEED_KEYS,
                       ConfigError, ScenarioSimulator, SimConfig,
                       UnknownCombinationClassifier, assign_rarity_counts,
                       compute_unknown_weight, compute_window_stats,
                       episode_transition_action)
from run_simulation import build_stats_json, build_summary

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


def conditional_config(rules, apply_to_initial_state=True, **over):
    return base_config(
        full_scenario_unknowns={"enabled": False},
        transition_model={
            "mode": "conditional",
            "conditional": {
                "apply_to_initial_state": apply_to_initial_state,
                "rules": rules,
            },
        },
        **over,
    )


_COUNTS = {"common": 37, "medium": 19, "rare": 8, "very_rare": 4, "unknown": 7}
_UNKNOWN_LAYERS = {"temporal_modifications", "ego_maneuver", "ru_maneuver",
                   "triggering_conditions"}


def _semantic_ego_layer():
    return {
        "mean_duration": 30.0,
        "variance_duration": 400.0,
        "allow_unknown": True,
        "semantic_catalog": {
            "version": "test-1.0",
            "elements": [
                {"id": "lane_follow", "label": "Lane following",
                 "description": "Continue in the current lane.",
                 "rarity": "common"},
                {"id": "merge", "label": "Merge",
                 "description": "Join another traffic stream.",
                 "rarity": "medium"},
                {"id": "emergency_braking", "label": "Emergency braking",
                 "description": "Perform high-urgency braking.",
                 "rarity": "very_rare"},
                {"id": "unclassified_ego_maneuver",
                 "label": "Unclassified ego maneuver",
                 "description": "A maneuver outside this catalog.",
                 "rarity": "unknown"},
            ],
        },
    }


def _layers_with_semantic_ego():
    return _layers(ego_maneuver=_semantic_ego_layer())


# ------------------------------------------------------ semantic catalogs (v5)

def test_default_config_uses_versioned_semantic_catalogs():
    config_path = Path(__file__).with_name("config.yaml")
    sim = ScenarioSimulator(SimConfig.from_yaml(str(config_path)))
    assert sim.layers[0].construction_mode == "fixed"
    for layer in sim.layers[1:]:
        assert layer.construction_mode == "semantic_catalog"
        assert layer.catalog_version == "1.0"
    assert "lane_follow" in sim.layers[2].names
    assert "cut_in" in sim.layers[3].names
    assert "fog" in sim.layers[4].names
    assert "sensor_occlusion" in sim.layers[5].names
    assert not any(name.startswith("ego_") for name in sim.layers[2].names)


def test_named_semantic_and_generated_profiles_are_distinct():
    root = Path(__file__).parent
    semantic_cfg = SimConfig.from_yaml(
        str(root / "config_semantic_catalog_v5s.yaml"))
    generated_cfg = SimConfig.from_yaml(
        str(root / "config_generated_elements_v5g.yaml"))
    semantic = ScenarioSimulator(semantic_cfg)
    generated = ScenarioSimulator(generated_cfg)

    assert semantic_cfg.profile_name == "semantic_catalog_v5s"
    assert semantic_cfg.profile_kind == "semantic_catalog"
    assert generated_cfg.profile_name == "generated_elements_v5g"
    assert generated_cfg.profile_kind == "generated_elements"

    assert semantic.layers[0].names == generated.layers[0].names
    assert semantic.layers[0].transition_probs.tolist() == \
        generated.layers[0].transition_probs.tolist()
    assert all(layer.construction_mode == "semantic_catalog"
               for layer in semantic.layers[1:])
    assert all(layer.construction_mode == "generated"
               for layer in generated.layers[1:])

    expected_ranges = {
        "temporal_modifications": (40, 45, "temporal_"),
        "ego_maneuver": (20, 24, "ego_"),
        "ru_maneuver": (20, 24, "ru_"),
        "environmental_conditions": (22, 22, "environment_"),
        "triggering_conditions": (80, 90, "trigger_"),
    }
    for layer in generated.layers[1:]:
        lower, upper, prefix = expected_ranges[layer.key]
        assert lower <= layer.n_elements <= upper
        assert all(name.startswith(prefix) for name in layer.names)
        assert layer.catalog_version is None

    assert "lane_follow" in semantic.layers[2].names
    assert "cut_in" in semantic.layers[3].names
    assert "fog" in semantic.layers[4].names
    assert "sensor_occlusion" in semantic.layers[5].names
    assert "lane_follow" not in generated.layers[2].names


def test_high_quality_semantic_catalog_v2_is_fixed_and_traceable():
    config_path = Path(__file__).with_name("config_semantic_catalog_v2.yaml")
    cfg = SimConfig.from_yaml(str(config_path))
    sim = ScenarioSimulator(cfg)

    assert cfg.profile_name == "semantic_catalog_v2_high_quality"
    expected_counts = {
        "street": 12,
        "temporal_modifications": 45,
        "ego_maneuver": 24,
        "ru_maneuver": 24,
        "environmental_conditions": 22,
        "triggering_conditions": 50,
    }
    assert {layer.key: layer.n_elements for layer in sim.layers} == \
        expected_counts

    for layer in sim.layers[1:]:
        assert layer.construction_mode == "semantic_catalog"
        assert layer.catalog_version == "2.0"
        assert layer.catalog_sources
        assert all(layer.families)
        assert all(layer.source_refs)
        assert all(set(refs) <= set(layer.catalog_sources)
                   for refs in layer.source_refs)

    assert "work_beyond_shoulder" in sim.layers[1].names
    assert "follow_lane" in sim.layers[2].names
    assert "passing_object" in sim.layers[3].names
    assert "heavy_rain_night" in sim.layers[4].names
    assert "radar_multipath" in sim.layers[5].names


def test_semantic_catalog_v2_requires_source_traceability():
    layer = copy.deepcopy(_semantic_ego_layer())
    layer["semantic_catalog"]["version"] = "2.0"
    with pytest.raises(ConfigError, match="requires sources"):
        base_config(layers=_layers(ego_maneuver=layer))


def test_semantic_catalog_identity_is_independent_of_construction_seeds():
    kwargs = {
        "layers": _layers_with_semantic_ego(),
        "full_scenario_unknowns": {"enabled": False},
    }
    first = ScenarioSimulator(base_config(
        seeds=seeds_with(element_count=1, rarity_assignment=2), **kwargs))
    second = ScenarioSimulator(base_config(
        seeds=seeds_with(element_count=999, rarity_assignment=888), **kwargs))
    for attribute in ("names", "labels", "descriptions", "rarities"):
        assert getattr(first.layers[2], attribute) == \
            getattr(second.layers[2], attribute)
    assert np.array_equal(first.layers[2].initial_probs,
                          second.layers[2].initial_probs)
    assert math.isclose(first.layers[2].designed_unknown_mass(), 0.004,
                        rel_tol=1e-12)


@pytest.mark.parametrize("mutation, expected", [
    (lambda layer: layer["semantic_catalog"]["elements"].append(
        dict(layer["semantic_catalog"]["elements"][0])), "unique"),
    (lambda layer: layer["semantic_catalog"]["elements"][0].update(
        rarity="frequent"), "rarity"),
    (lambda layer: layer.update(element_count_min=4,
                                element_count_max=4), "exactly one"),
])
def test_semantic_catalog_validation_rejects_invalid_definitions(
        mutation, expected):
    layer = copy.deepcopy(_semantic_ego_layer())
    mutation(layer)
    with pytest.raises(ConfigError) as error:
        base_config(layers=_layers(ego_maneuver=layer))
    assert expected in str(error.value)


def test_conditional_rules_resolve_stable_semantic_ids():
    cfg = conditional_config([{
        "id": "merge_context",
        "target_layer": "ego_maneuver",
        "when": {"street": {"elements": ["forced_merge_proceeding"]}},
        "multipliers": {"elements": {"merge": 4.0}},
    }], layers=_layers_with_semantic_ego())
    sim = ScenarioSimulator(cfg)
    current = [0] * len(sim.layers)
    current[0] = sim.layers[0].names.index("forced_merge_proceeding")
    evaluation = sim.conditional_model.evaluate(
        2, current, sim.layers[2].transition_probs)
    merge_index = sim.layers[2].names.index("merge")
    lane_follow_index = sim.layers[2].names.index("lane_follow")
    assert evaluation.matched_rule_ids == ("merge_context",)
    assert (evaluation.probabilities[merge_index]
            / evaluation.probabilities[lane_follow_index]) > (
                sim.layers[2].transition_probs[merge_index]
                / sim.layers[2].transition_probs[lane_follow_index])


def test_semantic_metadata_is_in_layer_statistics():
    cfg = base_config(
        layers=_layers_with_semantic_ego(),
        full_scenario_unknowns={"enabled": False},
        enable_unknown_combinations=False,
    )
    result = ScenarioSimulator(cfg).run()
    ego = result.layer_stats[2]
    assert ego["catalog_version"] == "test-1.0"
    assert ego["construction_mode"] == "semantic_catalog"
    merge = next(element for element in ego["elements"]
                 if element["id"] == "merge")
    assert merge["label"] == "Merge"
    assert merge["description"]
    assert merge["rarity"] == "medium"
    assert merge["visit_count"] >= 0
    assert 0.0 <= merge["realized_selection_rate"] <= 1.0


def test_legacy_generated_layers_remain_supported():
    sim = ScenarioSimulator(base_config(full_scenario_unknowns={"enabled": False}))
    ego = sim.layers[2]
    assert ego.construction_mode == "generated"
    assert ego.catalog_version is None
    assert all(name.startswith("ego_") for name in ego.names)


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


# ------------------------------------------------ conditional transition model

def _merge_ego_rule(rule_id="merge_affects_ego", multiplier=4.0):
    return {
        "id": rule_id,
        "target_layer": "ego_maneuver",
        "when": {
            "street": {
                "elements": [
                    "forced_merge_proceeding",
                    "forced_merge_merging",
                ],
            },
        },
        "multipliers": {"elements": {"ego_000": multiplier}},
    }


def test_transition_model_omitted_and_explicit_independent_are_bit_identical():
    omitted = ScenarioSimulator(
        base_config(target_total_miles=500.0)).run()
    explicit = ScenarioSimulator(base_config(
        target_total_miles=500.0,
        transition_model={
            "mode": "independent",
            "conditional": {
                "apply_to_initial_state": True,
                "rules": [],
            },
        },
    )).run()
    assert omitted.total_events == explicit.total_events
    assert omitted.total_miles == explicit.total_miles
    assert omitted.total_time_seconds == explicit.total_time_seconds
    assert omitted.total_unknown_time_seconds == \
        explicit.total_unknown_time_seconds
    assert omitted.episodes == explicit.episodes
    assert [row["visit_counts"] for row in omitted.layer_stats] == \
        [row["visit_counts"] for row in explicit.layer_stats]


def test_independent_mode_does_not_compile_or_evaluate_dormant_rules():
    dormant = _merge_ego_rule()
    dormant["multipliers"]["elements"] = {"not_a_real_element": 5.0}
    sim = ScenarioSimulator(base_config(
        transition_model={
            "mode": "independent",
            "conditional": {
                "apply_to_initial_state": True,
                "rules": [dormant],
            },
        },
    ))
    assert sim.conditional_model is None
    result = sim.run()
    assert result.transition_model_stats["mode"] == "independent"
    assert result.transition_model_stats["rules"][0]["active"] is False
    assert result.transition_model_stats["rules"][0]["match_count"] == 0


def test_conditional_matching_reweights_elements_and_rarities():
    rule = _merge_ego_rule(multiplier=4.0)
    rule["when"]["environmental_conditions"] = {
        "rarities": ["common", "medium"],
    }
    rule["multipliers"]["rarities"] = {"common": 1.5}
    sim = ScenarioSimulator(conditional_config([rule]))
    street = sim.layers[0]
    environment = sim.layers[4]
    current = [0] * len(sim.layers)
    current[0] = street.names.index("forced_merge_merging")
    current[4] = next(
        i for i, rarity in enumerate(environment.rarities)
        if rarity == "common")
    base = sim.layers[2].transition_probs
    rng_before = sim.rng_transition.getstate()
    actual = sim.conditional_model.probabilities_for(2, current, base)
    assert sim.rng_transition.getstate() == rng_before
    expected = base.copy()
    expected[sim.layers[2].names.index("ego_000")] *= 4.0
    for i, rarity in enumerate(sim.layers[2].rarities):
        if rarity == "common":
            expected[i] *= 1.5
    expected /= expected.sum()
    assert np.allclose(actual, expected)

    current[0] = street.names.index("constant_lane")
    unchanged = sim.conditional_model.probabilities_for(2, current, base)
    assert np.allclose(unchanged, base)


def test_conditional_selector_or_and_semantics():
    rule = _merge_ego_rule()
    rule["when"]["environmental_conditions"] = {
        "elements": ["environment_000"],
        "rarities": ["very_rare"],
    }
    sim = ScenarioSimulator(conditional_config([rule]))
    current = [0] * len(sim.layers)
    current[0] = sim.layers[0].names.index("forced_merge_proceeding")
    current[4] = sim.layers[4].names.index("environment_000")
    evaluation = sim.conditional_model.evaluate(
        2, current, sim.layers[2].transition_probs)
    assert evaluation.matched_rule_ids == ("merge_affects_ego",)

    # The street condition is false, so the cross-layer AND must fail even
    # though the environment condition still matches.
    current[0] = sim.layers[0].names.index("constant_lane")
    evaluation = sim.conditional_model.evaluate(
        2, current, sim.layers[2].transition_probs)
    assert evaluation.matched_rule_ids == ()


def test_multiple_rules_combine_multiplicatively_and_ignore_yaml_order():
    first = _merge_ego_rule("a_element", 2.0)
    second = {
        "id": "b_rarity",
        "target_layer": "ego_maneuver",
        "when": {
            "street": {"elements": ["forced_merge_merging"]},
        },
        "multipliers": {"rarities": {"common": 3.0}},
    }
    sim_a = ScenarioSimulator(conditional_config([first, second]))
    sim_b = ScenarioSimulator(conditional_config([second, first]))
    current = [0] * len(sim_a.layers)
    current[0] = sim_a.layers[0].names.index("forced_merge_merging")
    pa = sim_a.conditional_model.probabilities_for(
        2, current, sim_a.layers[2].transition_probs)
    pb = sim_b.conditional_model.probabilities_for(
        2, current, sim_b.layers[2].transition_probs)
    assert np.array_equal(pa, pb)


@pytest.mark.parametrize("transition_model", [
    {
        "mode": "conditional",
        "conditional": {
            "rules": [
                {
                    "id": "self",
                    "target_layer": "ego_maneuver",
                    "when": {"ego_maneuver": {"rarities": ["common"]}},
                    "multipliers": {"rarities": {"common": 2.0}},
                },
            ],
        },
    },
    {
        "mode": "conditional",
        "conditional": {
            "rules": [
                {
                    "id": "street_to_ego",
                    "target_layer": "ego_maneuver",
                    "when": {"street": {"rarities": ["common"]}},
                    "multipliers": {"rarities": {"common": 2.0}},
                },
                {
                    "id": "ego_to_street",
                    "target_layer": "street",
                    "when": {"ego_maneuver": {"rarities": ["common"]}},
                    "multipliers": {
                        "elements": {"constant_lane": 2.0},
                    },
                },
            ],
        },
    },
])
def test_conditional_self_dependencies_and_cycles_rejected(transition_model):
    with pytest.raises(ConfigError):
        base_config(
            full_scenario_unknowns={"enabled": False},
            transition_model=transition_model,
        )


def test_conditional_invalid_references_and_multipliers_rejected():
    bad_multiplier = _merge_ego_rule()
    bad_multiplier["multipliers"]["elements"]["ego_000"] = float("nan")
    with pytest.raises(ConfigError):
        conditional_config([bad_multiplier])

    duplicate = [_merge_ego_rule("same"), _merge_ego_rule("same")]
    with pytest.raises(ConfigError):
        conditional_config(duplicate)

    bad_element = _merge_ego_rule()
    bad_element["when"]["street"]["elements"] = ["does_not_exist"]
    with pytest.raises(ConfigError):
        ScenarioSimulator(conditional_config([bad_element]))


def test_conditional_zero_distribution_rejected_and_self_exclusion_applied():
    zero_rule = {
        "id": "zero_everything",
        "target_layer": "ego_maneuver",
        "when": {"street": {"elements": ["constant_lane"]}},
        "multipliers": {
            "rarities": {rarity: 0.0 for rarity in RARITIES},
        },
    }
    sim = ScenarioSimulator(conditional_config([zero_rule]))
    current = [0] * len(sim.layers)
    current[0] = sim.layers[0].names.index("constant_lane")
    with pytest.raises(ConfigError):
        sim.conditional_model.probabilities_for(
            2, current, sim.layers[2].transition_probs)

    empty = ScenarioSimulator(conditional_config([]))
    probs = empty.conditional_model.probabilities_for(
        2, [0] * len(empty.layers), empty.layers[2].transition_probs,
        current_element=0, allow_self_transition=False)
    assert probs[0] == 0.0
    assert math.isclose(float(probs.sum()), 1.0)


def test_conditional_initialization_uses_dependency_order():
    force_ego_zero = {
        "id": "initial_street_to_ego",
        "target_layer": "ego_maneuver",
        "when": {"street": {"elements": ["constant_lane"]}},
        "multipliers": {
            "elements": {
                **{f"ego_{i:03d}": 0.0 for i in range(12)},
                "ego_000": 1.0,
            },
        },
    }
    sim = ScenarioSimulator(conditional_config([force_ego_zero]))
    state = sim._new_state()
    assert sim.layers[0].names[state["current"][0]] == "constant_lane"
    assert sim.layers[2].names[state["current"][2]] == "ego_000"
    assert sim.conditional_model.dependency_order.index(0) < \
        sim.conditional_model.dependency_order.index(2)


def test_simultaneous_expiries_use_new_parent_state():
    rule = {
        "id": "environment_to_ego",
        "target_layer": "ego_maneuver",
        "when": {
            "environmental_conditions": {"rarities": ["rare"]},
        },
        "multipliers": {
            "rarities": {
                "common": 1.0,
                "medium": 0.0,
                "rare": 0.0,
                "very_rare": 0.0,
                "unknown": 0.0,
            },
        },
    }
    sim = ScenarioSimulator(conditional_config(
        [rule], apply_to_initial_state=False, target_total_miles=0.001))
    state = sim._new_state()
    environment = sim.layers[4]
    rare_index = next(
        i for i, rarity in enumerate(environment.rarities)
        if rarity == "rare")
    common_index = next(
        i for i, rarity in enumerate(environment.rarities)
        if rarity == "common")
    state["current"][4] = common_index
    state["current"][2] = next(
        i for i, rarity in enumerate(sim.layers[2].rarities)
        if rarity == "common")
    state["remaining"] = [100.0] * len(sim.layers)
    state["remaining"][2] = 1.0
    state["remaining"][4] = 1.0
    forced = np.zeros(environment.n_elements)
    forced[rare_index] = 1.0
    environment.transition_probs = forced
    environment.transition_cum = list(np.cumsum(forced))

    result, final_state = sim.run_resumable(state)
    assert result is not None
    assert environment.rarities[final_state["current"][4]] == "rare"
    assert sim.layers[2].rarities[final_state["current"][2]] == "common"
    assert sim.conditional_model.dependency_order.index(4) < \
        sim.conditional_model.dependency_order.index(2)


def test_conditional_checkpoint_resume_bit_identical():
    cfg = conditional_config(
        [_merge_ego_rule()], target_total_miles=200.0)
    full = ScenarioSimulator(cfg).run()
    resumed_sim = ScenarioSimulator(cfg)
    result, state = resumed_sim.run_resumable(
        state=None, wall_limit_seconds=0.0)
    assert result is None
    resumed_sim, state = pickle.loads(pickle.dumps((resumed_sim, state)))
    resumed, _state = resumed_sim.run_resumable(state)
    assert resumed.total_events == full.total_events
    assert resumed.total_time_seconds == full.total_time_seconds
    assert resumed.episodes == full.episodes
    assert resumed.transition_model_stats == full.transition_model_stats


def test_conditional_mode_rejects_independent_full_scenario_classifier():
    with pytest.raises(ConfigError, match="dependency-aware"):
        base_config(transition_model={
            "mode": "conditional",
            "conditional": {
                "apply_to_initial_state": True,
                "rules": [],
            },
        })


def test_conditional_outputs_include_diagnostics_and_unknown_warning():
    rule = {
        "id": "street_changes_unknown_prior",
        "target_layer": "ego_maneuver",
        "when": {"street": {"elements": ["constant_lane"]}},
        "multipliers": {"rarities": {"unknown": 2.0}},
    }
    result = ScenarioSimulator(conditional_config(
        [rule], target_total_miles=20.0)).run()
    inter_mi = result.inter_arrival_miles()
    inter_s = result.inter_arrival_seconds()
    ws = result.window_stats()
    stats = build_stats_json(result, inter_mi, inter_s, ws, 0.0)
    summary = build_summary(result, inter_mi, inter_s, ws, 0.0)
    assert stats["profile_name"] == "custom"
    assert stats["profile_kind"] == "custom"
    assert "simulator profile: `custom` (`custom`)" in summary
    assert stats["transition_model"]["mode"] == "conditional"
    assert stats["transition_model"]["rules"][0]["match_count"] > 0
    ego = next(row for row in stats["transition_model"]["layers"]
               if row["layer"] == "ego_maneuver")
    assert ego["selections_under_matched_context"]
    assert "baseline_unknown_mass" in ego
    assert "empirical_unknown_occupancy" in ego
    assert "Conditional-transition diagnostics" in summary
    assert "WARNING: conditional rules modify unknown-rarity" in summary


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
