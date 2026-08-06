"""Tests for the v6 time-bounded rare-combination simulator design."""

import copy
import json
import math
import pickle
import random
import shutil
import uuid
from pathlib import Path

import numpy as np
import pytest
import yaml

from simulator import (RARITIES, ConfigError,
                       ScenarioSimulator, SimConfig, assign_rarity_counts,
                       compute_window_stats)
from run_simulation import (build_element_rarity_composition, build_stats_json,
                             build_summary,
                             make_duration_distribution_plots)


CONFIG = Path(__file__).with_name("config.yaml")


def config(**changes):
    cfg = SimConfig.from_yaml(str(CONFIG))
    cfg.target_total_miles = None
    cfg.target_total_hours = 1.0
    cfg.mileage_window_miles = 10.0
    for key, value in changes.items():
        setattr(cfg, key, value)
    cfg.validate()
    return cfg


def test_default_config_has_only_requested_rarities():
    cfg = config()
    sim = ScenarioSimulator(cfg)
    assert RARITIES == ("common", "rare", "unknown")
    assert cfg.element_class_percentages == {
        "common": 70.0, "rare": 20.0, "unknown": 10.0}
    assert cfg.selection_class_percentages == {
        "common": 70.0, "rare": 20.0, "unknown": 10.0}
    assert all(set(layer.counts) == set(RARITIES) for layer in sim.layers)


@pytest.mark.parametrize("filename", [
    "config.yaml",
    "config_generated_elements_v5g.yaml",
])
def test_all_profiles_load_with_three_rarity_classes(filename):
    cfg = SimConfig.from_yaml(str(CONFIG.with_name(filename)))
    sim = ScenarioSimulator(cfg)
    assert all(set(layer.rarities) <= set(RARITIES) for layer in sim.layers)


def test_every_layer_is_generated_and_semantic_catalogs_are_rejected():
    cfg = config()
    sim = ScenarioSimulator(cfg)
    assert cfg.profile_kind == "generated_elements"
    assert all(layer.construction_mode == "generated" for layer in sim.layers)
    assert "semantic_catalog" not in CONFIG.read_text(encoding="utf-8")
    assert not CONFIG.with_name("config_semantic_catalog_v5s.yaml").exists()
    assert not CONFIG.with_name("config_semantic_catalog_v2.yaml").exists()


@pytest.mark.parametrize("obsolete_key", [
    "base_weights", "unknown_weight_mode",
    "target_unknown_element_probability", "fixed_unknown_weight",
])
def test_obsolete_weight_configuration_is_rejected(obsolete_key):
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw[obsolete_key] = 1
    with pytest.raises(ConfigError, match="Bad config keys"):
        SimConfig.from_dict(raw)


def test_old_rarity_categories_are_rejected():
    cfg = config()
    cfg.element_class_percentages["medium"] = 0.0
    with pytest.raises(ConfigError, match="exactly"):
        cfg.validate()


def test_rarity_counts_use_largest_remainder_and_sum_exactly():
    percentages = {"common": 70.0, "rare": 20.0, "unknown": 10.0}
    for n in range(5, 150):
        counts = assign_rarity_counts(n, percentages)
        assert set(counts) == set(RARITIES)
        assert sum(counts.values()) == n


def test_selection_class_percentages_are_exact_in_every_layer():
    cfg = config()
    sim = ScenarioSimulator(cfg)
    for layer in sim.layers:
        for rarity in RARITIES:
            expected = cfg.selection_class_percentages[rarity] / 100.0
            initial = sum(probability for probability, value
                          in zip(layer.initial_probs, layer.rarities)
                          if value == rarity)
            transition = sum(probability for probability, value
                             in zip(layer.transition_probs, layer.rarities)
                             if value == rarity)
            assert math.isclose(initial, expected, abs_tol=1e-12)
            assert math.isclose(transition, expected, abs_tol=1e-12)


def test_class_percentage_mappings_must_sum_to_100():
    cfg = config()
    cfg.selection_class_percentages["unknown"] = 9.0
    with pytest.raises(ConfigError, match="sum to 100"):
        cfg.validate()


def test_every_element_has_its_own_gamma_parameters():
    sim = ScenarioSimulator(config())
    for layer in sim.layers:
        n = layer.n_elements
        assert len(layer.duration_means) == n
        assert len(layer.duration_variances) == n
        assert len(layer.gamma_shapes) == n
        assert len(layer.gamma_scales) == n
        for i in range(n):
            assert layer.duration_means[i] > 0
            assert layer.duration_variances[i] > 0
            assert math.isclose(
                layer.gamma_shapes[i] * layer.gamma_scales[i],
                layer.duration_means[i], rel_tol=1e-12)


def test_duration_mean_bands_are_common_then_rare_then_unknown_per_layer():
    sim = ScenarioSimulator(config())
    for layer in sim.layers:
        by_rarity = {
            rarity: [layer.duration_means[i]
                     for i, value in enumerate(layer.rarities)
                     if value == rarity]
            for rarity in RARITIES
        }
        if by_rarity["common"] and by_rarity["rare"]:
            assert min(by_rarity["common"]) > max(by_rarity["rare"])
        if by_rarity["rare"] and by_rarity["unknown"]:
            assert min(by_rarity["rare"]) > max(by_rarity["unknown"])
        for values in by_rarity.values():
            if len(values) > 1:
                assert len(set(values)) == len(values)


def test_duration_sampling_uses_current_element_and_clamps_minimum():
    layer = ScenarioSimulator(config()).layers[2]
    rng = random.Random(9)
    values = [layer.sample_duration(rng, 0, 25.0) for _ in range(5000)]
    assert min(values) >= 25.0


def test_duration_profiles_must_have_ordered_non_overlapping_bands():
    cfg = config()
    cfg.duration_profiles["rare"]["mean_multiplier"] = 2.0
    with pytest.raises(ConfigError, match="common > rare > unknown"):
        cfg.validate()


def test_selected_rule_counts_sizes_and_trigger_requirement():
    sim = ScenarioSimulator(config())
    expected = {3: 40, 4: 30, 5: 20, 6: 10}
    assert {size: sum(rule.size == size for rule in sim.rules)
            for size in expected} == expected
    for rule in sim.rules:
        assert len({layer for layer, _element in rule.items}) == rule.size
        assert any(layer == 5 for layer, _element in rule.items)
        assert all(sim.layers[layer].rarities[element] == "rare"
                   for layer, element in rule.items)
        assert rule.description.startswith(f"C{rule.size}: ")


def test_rule_selection_is_seeded_and_reproducible():
    first = ScenarioSimulator(config())
    second = ScenarioSimulator(config())
    assert [rule.items for rule in first.rules] == [rule.items for rule in second.rules]
    changed_cfg = config()
    changed_cfg.seeds = dict(changed_cfg.seeds, combination_selection=999)
    changed = ScenarioSimulator(changed_cfg)
    assert [rule.items for rule in first.rules] != [rule.items for rule in changed.rules]
    assert [layer.names for layer in first.layers] == [layer.names for layer in changed.layers]


def test_requesting_more_combinations_than_exist_is_rejected():
    cfg = config()
    cfg.unknown_scenarios["combination_counts"] = {3: 10**9, 4: 0, 5: 0, 6: 0}
    cfg.validate()
    with pytest.raises(ConfigError, match="eligible"):
        ScenarioSimulator(cfg)


def _common_state(sim):
    return [next(i for i, rarity in enumerate(layer.rarities)
                 if rarity == "common") for layer in sim.layers]


def test_exact_rare_set_matching_and_unknown_disqualification():
    sim = ScenarioSimulator(config())
    rule = next(rule for rule in sim.rules if rule.size == 3)
    current = _common_state(sim)
    for layer, element in rule.items:
        current[layer] = element
    assert sim.matched_combination_rule(current) == rule

    unrelated = next(layer for layer in range(6)
                     if layer not in {k for k, _ in rule.items})
    current[unrelated] = next(
        i for i, rarity in enumerate(sim.layers[unrelated].rarities)
        if rarity == "rare")
    assert sim.matched_combination_rule(current) is None

    current = _common_state(sim)
    for layer, element in rule.items:
        current[layer] = element
    unknown_layer = next(
        k for k, layer in enumerate(sim.layers)
        if k not in {item[0] for item in rule.items} and layer.has_unknown())
    current[unknown_layer] = sim.layers[unknown_layer].is_unknown.index(True)
    assert sim.matched_combination_rule(current) is None


def test_unknown_rarity_elements_do_not_open_standalone_episodes():
    result = ScenarioSimulator(config(target_total_hours=100.0)).run()
    assert all(episode.type == "rare_combination" for episode in result.episodes)
    assert all(row["episodes"] == 0 for row in result.layer_stats)


@pytest.mark.parametrize("obsolete_key", [
    "enable_unknown_combinations", "enable_hash_combinations",
    "enable_hidden_triggering_unknowns", "combination_rules",
    "unknown_combination_probability", "full_scenario_unknowns", "global_seed",
])
def test_removed_unknown_scenario_methods_are_rejected(obsolete_key):
    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw[obsolete_key] = False
    with pytest.raises(ConfigError, match="Bad config keys"):
        SimConfig.from_dict(raw)


def test_simulation_stops_exactly_at_configured_time():
    cfg = config(target_total_hours=2.5)
    result = ScenarioSimulator(cfg).run()
    assert result.total_time_seconds == 2.5 * 3600.0
    assert math.isclose(result.total_miles, 2.5 * cfg.average_speed_mph,
                        rel_tol=1e-12)


def test_time_boundary_does_not_overshoot_first_event():
    cfg = config(target_total_hours=1e-8)
    result = ScenarioSimulator(cfg).run()
    assert result.total_time_seconds == cfg.target_time_seconds
    assert result.total_events == 0


def test_legacy_mileage_input_is_converted_to_a_time_target():
    cfg = config(target_total_hours=20_000.0, target_total_miles=25.0)
    result = ScenarioSimulator(cfg).run()
    assert result.total_time_seconds == 25.0 / cfg.average_speed_mph * 3600.0
    assert math.isclose(result.total_miles, 25.0, abs_tol=1e-12)


def test_checkpoint_resume_is_bit_identical():
    cfg = config(target_total_hours=10.0)
    full = ScenarioSimulator(cfg).run()
    resumed_sim = ScenarioSimulator(cfg)
    result, state = resumed_sim.run_resumable(None, wall_limit_seconds=0.0)
    assert result is None
    resumed_sim, state = pickle.loads(pickle.dumps((resumed_sim, state)))
    resumed, _ = resumed_sim.run_resumable(state)
    assert resumed.total_events == full.total_events
    assert resumed.total_time_seconds == full.total_time_seconds
    assert resumed.episodes == full.episodes


def test_result_metadata_exposes_element_duration_laws():
    result = ScenarioSimulator(config()).run()
    for layer in result.layer_stats:
        for element in layer["elements"]:
            assert element["duration_distribution"] == "gamma"
            assert element["duration_mean_seconds"] > 0
            assert element["duration_variance_seconds2"] > 0


def test_duration_distribution_folder_contains_one_plot_per_layer():
    temporary = Path.cwd() / f".test-duration-plots-{uuid.uuid4().hex}"
    try:
        result = ScenarioSimulator(config()).run()
        output_dir = temporary / "duration_distributions"
        manifest = make_duration_distribution_plots(result, output_dir)

        assert (output_dir / "manifest.json").is_file()
        saved = json.loads((output_dir / "manifest.json").read_text("utf-8"))
        assert saved == manifest
        assert len(manifest["layers"]) == len(result.layer_stats) == 6
        for layer in manifest["layers"]:
            plot = output_dir / layer["file"]
            assert plot.is_file() and plot.stat().st_size > 1_000
            available = {
                element["rarity"] for row in result.layer_stats
                if row["layer"] == layer["layer"]
                for element in row["elements"]
            }
            assert {element["rarity"] for element in layer["elements"]} \
                == available
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def test_output_builders_describe_v6_without_legacy_keys():
    result = ScenarioSimulator(config(target_total_hours=10.0)).run()
    inter_miles = result.inter_arrival_miles()
    inter_seconds = result.inter_arrival_seconds()
    windows = result.window_stats()
    summary = build_summary(result, inter_miles, inter_seconds, windows, 0.1)
    stats = build_stats_json(result, inter_miles, inter_seconds, windows, 0.1)
    assert "target simulated time" in summary
    assert "exact rare-element combinations" in summary
    assert stats["combination_stats"]["mechanism"] == \
        "exact_rare_element_combinations"
    assert "## Element rarity composition" in summary
    composition = stats["element_rarity_composition"]
    assert composition == build_element_rarity_composition(result)
    assert composition["configured_element_class_percentages"] == {
        "common": 70.0, "rare": 20.0, "unknown": 10.0}
    assert composition["configured_selection_class_percentages"] == {
        "common": 70.0, "rare": 20.0, "unknown": 10.0}
    assert sum(composition["all_layers_total"]["counts"].values()) == \
        composition["all_layers_total"]["total_elements"]
    for row in composition["layers"]:
        assert math.isclose(sum(row["proportions"].values()), 1.0)


def test_window_statistics_remain_consistent_for_derived_mileage():
    stats = compute_window_stats([5.0, 15.0, 25.0, 25.5, 999.0], 40.0, 10.0)
    assert stats["counts"] == [1, 1, 2, 0]
    assert stats["n_windows"] == 4
    assert math.isclose(stats["mean_count"], 1.0)


def test_transition_vectors_and_duration_parameters_are_seed_isolated():
    reference = ScenarioSimulator(config())
    changed_cfg = config()
    changed_cfg.seeds = dict(changed_cfg.seeds, duration=999)
    changed = ScenarioSimulator(changed_cfg)
    for first, second in zip(reference.layers, changed.layers):
        assert np.array_equal(first.transition_probs, second.transition_probs)
        assert first.duration_means == second.duration_means


def test_conditional_transition_model_still_uses_three_rarity_classes():
    cfg = config()
    cfg.transition_model = {
        "mode": "conditional",
        "conditional": {
            "apply_to_initial_state": True,
            "rules": [{
                "id": "merge_affects_ego",
                "target_layer": "ego_maneuver",
                "when": {"street": {"rarities": ["rare"]}},
                "multipliers": {"rarities": {"rare": 2.0}},
            }],
        },
    }
    sim = ScenarioSimulator(cfg)
    current = _common_state(sim)
    current[0] = next(i for i, rarity in enumerate(sim.layers[0].rarities)
                      if rarity == "rare")
    evaluation = sim.conditional_model.evaluate(
        2, current, sim.layers[2].transition_probs)
    assert evaluation.matched_rule_ids == ("merge_affects_ego",)
    assert evaluation.distribution_modified


def test_rule_statistics_are_internally_consistent():
    result = ScenarioSimulator(config(target_total_hours=100.0)).run()
    stats = result.combination_stats
    assert stats["episodes"] == sum(rule["episodes"] for rule in stats["rules"])
    assert stats["episodes"] == sum(stats["episodes_by_size"].values())
    assert result.episodes_by_type().get("rare_combination", 0) == stats["episodes"]
