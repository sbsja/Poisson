"""Event-driven six-layer scenario simulator (configuration v6).

Only ``common``, ``rare``, and ``unknown`` rarity classes exist. Every element
has its own Gamma sojourn-time distribution, derived reproducibly from its
layer baseline and rarity profile; configured mean bands are ordered common >
rare > unknown within every layer.

An unknown *scenario* is no longer a standalone unknown element, hash, or
stationary-probability threshold. At initialization the simulator selects
configured numbers of exact C3, C4, C5, and C6 combinations. Every combination
contains rare elements from distinct layers and must include one rare element
from ``triggering_conditions``. A rule matches only when the complete active
rare-element set equals the selected set and every other active element is
common. Unknown-rarity elements therefore disqualify a match.

The main loop stops exactly at ``target_total_hours`` (20,000 by default).
Mileage remains a derived reporting quantity. Independent and conditional
transition modes and bit-identical checkpoint/resume are retained.
"""

from __future__ import annotations

import bisect
import copy
import itertools
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

RARITIES = ("common", "rare", "unknown")
KNOWN_RARITIES = ("common", "rare")

SEED_KEYS = ("element_count", "rarity_assignment", "transition_matrix",
             "duration", "initial_state", "transition_sampling",
             "combination_selection")

#: (config key, element-name prefix) for the six layers, in fixed tuple order.
LAYER_DEFINITIONS = (
    ("street", "street"),
    ("temporal_modifications", "temporal"),
    ("ego_maneuver", "ego"),
    ("ru_maneuver", "ru"),
    ("environmental_conditions", "environment"),
    ("triggering_conditions", "trigger"),
)
N_LAYERS = len(LAYER_DEFINITIONS)
TRIGGERING_LAYER_INDEX = N_LAYERS - 1


class ConfigError(ValueError):
    """Invalid or inconsistent configuration."""


# ---------------------------------------------------------------- configuration

@dataclass
class LayerParams:
    mean_duration: float                 # seconds
    variance_duration: float             # seconds^2
    element_count_min: int
    element_count_max: int


def _default_seeds():
    return {"element_count": 12345, "rarity_assignment": 23456,
            "transition_matrix": 34567, "duration": 45678,
            "initial_state": 56789, "transition_sampling": 67890,
            "combination_selection": 78901}


def _default_element_class_percentages():
    return {"common": 70.0, "rare": 20.0, "unknown": 10.0}


def _default_selection_class_percentages():
    return {"common": 70.0, "rare": 20.0, "unknown": 10.0}


def _default_duration_profiles():
    """Rarity-level defaults used to derive one Gamma law per element.

    The multiplier bands do not overlap, even after applying element_spread,
    so the configured element means are always ordered common > rare > unknown.
    """
    return {
        "common": {"mean_multiplier": 1.50,
                   "coefficient_of_variation": 0.45,
                   "element_spread": 0.10},
        "rare": {"mean_multiplier": 0.75,
                 "coefficient_of_variation": 0.60,
                 "element_spread": 0.10},
        "unknown": {"mean_multiplier": 0.25,
                    "coefficient_of_variation": 0.80,
                    "element_spread": 0.10},
    }


def _default_unknown_scenarios():
    return {
        "enabled": True,
        "combination_counts": {3: 40, 4: 30, 5: 20, 6: 10},
        "require_triggering_condition": True,
        "exact_rare_set": True,
    }


def _default_transition_model():
    return {
        "mode": "independent",
        "conditional": {"apply_to_initial_state": True, "rules": []},
    }


@dataclass
class SimConfig:
    profile_name: str = "custom"
    profile_kind: str = "custom"
    seeds: dict = field(default_factory=_default_seeds)
    target_total_hours: float = 20_000.0
    # Compatibility input for old experiments. The event loop is time-based;
    # when supplied, this is converted to hours before the run begins.
    target_total_miles: float = None
    average_speed_mph: float = 50.0
    min_duration_seconds: float = 1.0
    mileage_window_miles: float = 10_000.0
    unknown_scenarios: dict = field(default_factory=_default_unknown_scenarios)
    element_class_percentages: dict = field(
        default_factory=_default_element_class_percentages)
    selection_class_percentages: dict = field(
        default_factory=_default_selection_class_percentages)
    duration_profiles: dict = field(default_factory=_default_duration_profiles)
    transition_model: dict = field(default_factory=_default_transition_model)
    concentration_scale: float = 20_000.0
    allow_self_transition: bool = True
    layers: dict = field(default_factory=dict)   # layer key -> LayerParams

    @property
    def target_time_seconds(self) -> float:
        hours = (self.target_total_miles / self.average_speed_mph
                 if self.target_total_miles is not None
                 else self.target_total_hours)
        return float(hours) * 3600.0

    # -- construction --------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str) -> "SimConfig":
        raw = cls._load_yaml_profile(Path(path), ())
        return cls.from_dict(raw)

    @classmethod
    def _load_yaml_profile(cls, path: Path, chain: tuple) -> dict:
        """Load YAML with an optional recursively resolved ``extends``."""
        resolved = path.resolve()
        if resolved in chain:
            cycle = " -> ".join(str(item) for item in chain + (resolved,))
            raise ConfigError(f"Configuration profile inheritance cycle: {cycle}")
        try:
            with resolved.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except OSError as exc:
            raise ConfigError(
                f"Cannot read configuration profile {str(resolved)!r}: {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise ConfigError(
                f"Configuration profile {str(resolved)!r} must contain a mapping.")

        raw = dict(raw)
        parent = raw.pop("extends", None)
        if parent is None:
            return raw
        if not isinstance(parent, str) or not parent.strip():
            raise ConfigError("Configuration 'extends' must be a non-empty path.")
        parent_path = (resolved.parent / parent).resolve()
        parent_raw = cls._load_yaml_profile(parent_path, chain + (resolved,))
        return cls._deep_merge(parent_raw, raw)

    @classmethod
    def _deep_merge(cls, parent: dict, child: dict) -> dict:
        """Merge a compact profile override into a complete parent config."""
        merged = copy.deepcopy(parent)
        for key, value in child.items():
            if (key in merged and isinstance(merged[key], dict)
                    and isinstance(value, dict)):
                merged[key] = cls._deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    @classmethod
    def from_dict(cls, raw: dict) -> "SimConfig":
        raw = dict(raw)
        layers_raw = raw.pop("layers", None)
        try:
            cfg = cls(**raw)
        except TypeError as exc:
            raise ConfigError(f"Bad config keys: {exc}") from exc
        if not layers_raw:
            raise ConfigError("Config must define 'layers'.")
        try:
            cfg.layers = {k: LayerParams(**v) for k, v in layers_raw.items()}
        except TypeError as exc:
            raise ConfigError(f"Bad layer config: {exc}") from exc
        cfg.validate()
        return cfg

    # -- helpers ---------------------------------------------------------------
    # -- validation -----------------------------------------------------------
    def validate(self) -> None:
        if not isinstance(self.profile_name, str) or not self.profile_name.strip():
            raise ConfigError("profile_name must be a non-empty string.")
        if self.profile_kind not in ("generated_elements", "custom"):
            raise ConfigError(
                "profile_kind must be 'generated_elements' or 'custom'.")
        if not isinstance(self.seeds, dict):
            raise ConfigError("'seeds' must be a mapping.")
        missing = [k for k in SEED_KEYS if k not in self.seeds]
        if missing:
            raise ConfigError(f"seeds missing entries: {missing}")
        unknown_keys = [k for k in self.seeds if k not in SEED_KEYS]
        if unknown_keys:
            raise ConfigError(f"seeds has unknown entries: {unknown_keys}")
        for k in SEED_KEYS:
            v = self.seeds[k]
            if isinstance(v, bool) or not isinstance(v, int):
                raise ConfigError(f"seeds[{k}] must be an integer, got {v!r}")

        self._validate_transition_model()

        scenarios = self.unknown_scenarios
        if not isinstance(scenarios, dict):
            raise ConfigError("unknown_scenarios must be a mapping.")
        scenario_allowed = {"enabled", "combination_counts",
                            "require_triggering_condition", "exact_rare_set"}
        bad = [key for key in scenarios if key not in scenario_allowed]
        if bad:
            raise ConfigError(f"unknown_scenarios has unknown keys: {bad}")
        scenarios.setdefault("enabled", True)
        scenarios.setdefault("combination_counts", {3: 40, 4: 30, 5: 20, 6: 10})
        scenarios.setdefault("require_triggering_condition", True)
        scenarios.setdefault("exact_rare_set", True)
        if not isinstance(scenarios["enabled"], bool):
            raise ConfigError("unknown_scenarios.enabled must be a bool.")
        if scenarios["require_triggering_condition"] is not True:
            raise ConfigError(
                "unknown_scenarios.require_triggering_condition must be true; "
                "every C3-C6 rule requires a rare triggering condition.")
        if scenarios["exact_rare_set"] is not True:
            raise ConfigError(
                "unknown_scenarios.exact_rare_set must be true; subset matches "
                "would make C3-C6 categories overlap.")
        counts = scenarios["combination_counts"]
        if not isinstance(counts, dict):
            raise ConfigError(
                "unknown_scenarios.combination_counts must be a mapping.")
        normalized_counts = {}
        for raw_size, raw_count in counts.items():
            try:
                size = int(raw_size)
            except (TypeError, ValueError):
                raise ConfigError(
                    "unknown_scenarios combination sizes must be 3, 4, 5, or 6."
                ) from None
            if size not in (3, 4, 5, 6) or str(raw_size) != str(size):
                raise ConfigError(
                    "unknown_scenarios combination sizes must be 3, 4, 5, or 6.")
            if (isinstance(raw_count, bool) or not isinstance(raw_count, int)
                    or raw_count < 0):
                raise ConfigError(
                    f"unknown_scenarios.combination_counts[{size}] must be a "
                    "non-negative integer.")
            normalized_counts[size] = raw_count
        scenarios["combination_counts"] = {
            size: normalized_counts.get(size, 0) for size in (3, 4, 5, 6)}


        for field_name in ("element_class_percentages",
                           "selection_class_percentages"):
            percentages = getattr(self, field_name)
            if not isinstance(percentages, dict):
                raise ConfigError(f"{field_name} must be a mapping.")
            if set(percentages) != set(RARITIES):
                raise ConfigError(
                    f"{field_name} must contain exactly {RARITIES}.")
            for rarity in RARITIES:
                value = percentages[rarity]
                if (isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        or float(value) <= 0):
                    raise ConfigError(
                        f"{field_name}[{rarity}] must be a positive percentage.")
            total = sum(float(percentages[r]) for r in RARITIES)
            if abs(total - 100.0) > 1e-6:
                raise ConfigError(
                    f"{field_name} must sum to 100.0 (got {total}).")

        if not isinstance(self.duration_profiles, dict):
            raise ConfigError("duration_profiles must be a mapping.")
        if set(self.duration_profiles) != set(RARITIES):
            raise ConfigError(
                f"duration_profiles must contain exactly {RARITIES}.")
        mean_bands = {}
        for rarity in RARITIES:
            profile = self.duration_profiles[rarity]
            if not isinstance(profile, dict):
                raise ConfigError(f"duration_profiles[{rarity}] must be a mapping.")
            expected = {"mean_multiplier", "coefficient_of_variation",
                        "element_spread"}
            if set(profile) != expected:
                raise ConfigError(
                    f"duration_profiles[{rarity}] must contain exactly "
                    f"{sorted(expected)}.")
            multiplier = float(profile["mean_multiplier"])
            cv = float(profile["coefficient_of_variation"])
            spread = float(profile["element_spread"])
            if not math.isfinite(multiplier) or multiplier <= 0:
                raise ConfigError(f"duration_profiles[{rarity}].mean_multiplier "
                                  "must be positive.")
            if not math.isfinite(cv) or cv <= 0:
                raise ConfigError(
                    f"duration_profiles[{rarity}].coefficient_of_variation "
                    "must be positive.")
            if not math.isfinite(spread) or not (0 <= spread < 1):
                raise ConfigError(f"duration_profiles[{rarity}].element_spread "
                                  "must be in [0, 1).")
            mean_bands[rarity] = (multiplier * (1.0 - spread),
                                  multiplier * (1.0 + spread))
        if not (mean_bands["common"][0] > mean_bands["rare"][1]
                > mean_bands["unknown"][1]):
            raise ConfigError(
                "duration_profiles mean bands must not overlap and must be "
                "ordered common > rare > unknown.")

        if self.average_speed_mph <= 0:
            raise ConfigError("average_speed_mph must be positive.")
        if self.target_total_hours <= 0:
            raise ConfigError("target_total_hours must be positive.")
        if self.target_total_miles is not None and self.target_total_miles <= 0:
            raise ConfigError("target_total_miles must be positive when used.")
        if self.min_duration_seconds <= 0:
            raise ConfigError("min_duration_seconds must be positive.")
        if self.concentration_scale <= 0:
            raise ConfigError("concentration_scale must be positive.")
        if self.mileage_window_miles <= 0:
            raise ConfigError("mileage_window_miles must be positive.")

        for key, _prefix in LAYER_DEFINITIONS:
            if key not in self.layers:
                raise ConfigError(f"Missing config for layer '{key}'.")
            lp = self.layers[key]
            if lp.mean_duration <= 0 or lp.variance_duration <= 0:
                raise ConfigError(f"Layer '{key}': durations must be positive.")
            if not (0 < lp.element_count_min <= lp.element_count_max):
                raise ConfigError(
                    f"Layer '{key}': require 0 < element_count_min <= "
                    "element_count_max.")
            for n in range(lp.element_count_min, lp.element_count_max + 1):
                counts = assign_rarity_counts(
                    n, self.element_class_percentages)
                missing = [rarity for rarity in RARITIES
                           if counts[rarity] == 0]
                if missing:
                    raise ConfigError(
                        f"Layer '{key}': element count n={n} yields no "
                        f"elements for {missing}; increase the count or the "
                        "corresponding element_class_percentages.")

        extra = [k for k in self.layers
                 if k not in [key for key, _ in LAYER_DEFINITIONS]]
        if extra:
            raise ConfigError(f"Unknown layer keys in config: {extra}")

    def _validate_transition_model(self) -> None:
        tm = self.transition_model
        if not isinstance(tm, dict):
            raise ConfigError("transition_model must be a mapping.")
        allowed = {"mode", "conditional"}
        bad = [k for k in tm if k not in allowed]
        if bad:
            raise ConfigError(f"transition_model has unknown keys: {bad}")
        tm.setdefault("mode", "independent")
        tm.setdefault("conditional",
                      {"apply_to_initial_state": True, "rules": []})
        if tm["mode"] not in ("independent", "conditional"):
            raise ConfigError(
                "transition_model.mode must be 'independent' or "
                f"'conditional', got {tm['mode']!r}.")

        cond = tm["conditional"]
        if not isinstance(cond, dict):
            raise ConfigError("transition_model.conditional must be a mapping.")
        allowed_cond = {"apply_to_initial_state", "rules"}
        bad = [k for k in cond if k not in allowed_cond]
        if bad:
            raise ConfigError(
                "transition_model.conditional has unknown keys: "
                f"{bad}")
        cond.setdefault("apply_to_initial_state", True)
        cond.setdefault("rules", [])
        if not isinstance(cond["apply_to_initial_state"], bool):
            raise ConfigError(
                "transition_model.conditional.apply_to_initial_state must "
                "be a bool.")
        if not isinstance(cond["rules"], list):
            raise ConfigError(
                "transition_model.conditional.rules must be a list.")

        layer_keys = {key for key, _prefix in LAYER_DEFINITIONS}
        seen_ids = set()
        edges = {key: set() for key in layer_keys}
        for pos, rule in enumerate(cond["rules"]):
            where = f"transition_model.conditional.rules[{pos}]"
            if not isinstance(rule, dict):
                raise ConfigError(f"{where} must be a mapping.")
            allowed_rule = {"id", "target_layer", "when", "multipliers"}
            bad = [k for k in rule if k not in allowed_rule]
            if bad:
                raise ConfigError(f"{where} has unknown keys: {bad}")
            missing = [k for k in allowed_rule if k not in rule]
            if missing:
                raise ConfigError(f"{where} is missing keys: {missing}")

            rule_id = rule["id"]
            if not isinstance(rule_id, str) or not rule_id.strip():
                raise ConfigError(f"{where}.id must be a non-empty string.")
            if rule_id in seen_ids:
                raise ConfigError(
                    f"Duplicate conditional rule id: {rule_id!r}.")
            seen_ids.add(rule_id)

            target = rule["target_layer"]
            if target not in layer_keys:
                raise ConfigError(
                    f"{where}.target_layer is unknown: {target!r}.")
            when = rule["when"]
            if not isinstance(when, dict) or not when:
                raise ConfigError(f"{where}.when must be a non-empty mapping.")
            for parent, selector in when.items():
                if parent not in layer_keys:
                    raise ConfigError(
                        f"{where}.when references unknown layer {parent!r}.")
                if parent == target:
                    raise ConfigError(
                        f"{where} makes layer {target!r} condition on itself.")
                self._validate_condition_selector(
                    selector, f"{where}.when[{parent!r}]")
                edges[parent].add(target)

            multipliers = rule["multipliers"]
            if not isinstance(multipliers, dict) or not multipliers:
                raise ConfigError(
                    f"{where}.multipliers must be a non-empty mapping.")
            allowed_mult = {"elements", "rarities"}
            bad = [k for k in multipliers if k not in allowed_mult]
            if bad:
                raise ConfigError(
                    f"{where}.multipliers has unknown keys: {bad}")
            if not any(multipliers.get(k) for k in allowed_mult):
                raise ConfigError(
                    f"{where}.multipliers must contain at least one effect.")
            element_effects = multipliers.get("elements", {})
            rarity_effects = multipliers.get("rarities", {})
            if not isinstance(element_effects, dict):
                raise ConfigError(
                    f"{where}.multipliers.elements must be a mapping.")
            if not isinstance(rarity_effects, dict):
                raise ConfigError(
                    f"{where}.multipliers.rarities must be a mapping.")
            for element, value in element_effects.items():
                if not isinstance(element, str) or not element:
                    raise ConfigError(
                        f"{where}.multipliers.elements keys must be "
                        "non-empty strings.")
                self._validate_multiplier(
                    value, f"{where}.multipliers.elements[{element!r}]")
            for rarity, value in rarity_effects.items():
                if rarity not in RARITIES:
                    raise ConfigError(
                        f"{where}.multipliers.rarities has unknown rarity "
                        f"{rarity!r}.")
                self._validate_multiplier(
                    value, f"{where}.multipliers.rarities[{rarity!r}]")

        # Stable Kahn traversal doubles as an early cycle check. Exact element
        # references are validated after seeded layers have been constructed.
        indegree = {key: 0 for key in layer_keys}
        for parent in layer_keys:
            for child in edges[parent]:
                indegree[child] += 1
        order = []
        remaining = set(layer_keys)
        fixed_order = [key for key, _prefix in LAYER_DEFINITIONS]
        while remaining:
            ready = [key for key in fixed_order
                     if key in remaining and indegree[key] == 0]
            if not ready:
                raise ConfigError(
                    "Conditional transition dependencies contain a cycle.")
            for parent in ready:
                remaining.remove(parent)
                order.append(parent)
                for child in edges[parent]:
                    indegree[child] -= 1

    @staticmethod
    def _validate_condition_selector(selector, where):
        if not isinstance(selector, dict) or not selector:
            raise ConfigError(f"{where} must be a non-empty mapping.")
        allowed = {"elements", "rarities"}
        bad = [k for k in selector if k not in allowed]
        if bad:
            raise ConfigError(f"{where} has unknown keys: {bad}")
        if not any(selector.get(k) for k in allowed):
            raise ConfigError(
                f"{where} must contain non-empty elements or rarities.")
        elements = selector.get("elements", [])
        rarities = selector.get("rarities", [])
        if not isinstance(elements, list) or any(
                not isinstance(value, str) or not value for value in elements):
            raise ConfigError(
                f"{where}.elements must be a list of non-empty strings.")
        if len(set(elements)) != len(elements):
            raise ConfigError(f"{where}.elements contains duplicates.")
        if not isinstance(rarities, list) or any(
                value not in RARITIES for value in rarities):
            raise ConfigError(
                f"{where}.rarities must contain only {RARITIES}.")
        if len(set(rarities)) != len(rarities):
            raise ConfigError(f"{where}.rarities contains duplicates.")

    @staticmethod
    def _validate_multiplier(value, where):
        if (isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0):
            raise ConfigError(
                f"{where} must be a finite non-negative number.")


# ------------------------------------------------------- rarity / weight helpers

def assign_rarity_counts(n_elements: int, percentages: dict) -> dict:
    """Largest-remainder integer counts from percentages summing to 100."""
    exact = {r: n_elements * percentages[r] / 100.0 for r in RARITIES}
    counts = {r: math.floor(exact[r]) for r in RARITIES}
    remainder = n_elements - sum(counts.values())
    by_fraction = sorted(RARITIES, key=lambda r: -(exact[r] - counts[r]))
    for r in by_fraction[:remainder]:
        counts[r] += 1
    return counts



# ------------------------------------------------------------- sampling helpers

def sample_index_from_cum(cum, n, u):
    i = bisect.bisect_right(cum, u)
    return i if i < n else n - 1


def sample_next_index(cum, n, rng, current, allow_self):
    """Categorical sample from a fixed cumulative vector; rejection-samples
    when self-transitions are disabled."""
    for _ in range(1_000_000):
        i = sample_index_from_cum(cum, n, rng.random())
        if allow_self or i != current:
            return i
    raise RuntimeError("Self-transition rejection sampling failed.")


def sample_gamma_duration(rng, shape, scale, min_duration):
    d = rng.gammavariate(shape, scale)
    return d if d > min_duration else min_duration


def episode_transition_action(cur_unknown, nxt_unknown, same_element):
    """Episode rules 1-4 for one layer transition.

    Returns (close_current_episode, open_new_episode).
      known  -> unknown              : (False, True)   rule 1
      unknown -> known               : (True, False)   rule 2
      unknown -> different unknown   : (True, True)    rule 3 (restart)
      unknown -> same unknown (self) : (False, False)  rule 4 (continues)
      known  -> known                : (False, False)
    """
    if cur_unknown:
        if same_element:
            return (False, False)
        if nxt_unknown:
            return (True, True)
        return (True, False)
    return (False, nxt_unknown)


# ------------------------------------------------------------ output statistics

def compute_window_stats(positions_miles, total_miles, window_miles):
    """Counts per complete fixed mileage window + mean/variance/dispersion.
    Only complete windows inside total_miles are used (no partial-window
    bias). Sample variance (ddof=1); dispersion = variance/mean."""
    n_windows = int(total_miles // window_miles)
    if n_windows < 1:
        raise ValueError("mileage_window_miles larger than the total mileage.")
    counts = [0] * n_windows
    for m in positions_miles:
        i = int(m // window_miles)
        if i < n_windows:
            counts[i] += 1
    mean = sum(counts) / n_windows
    var = (sum((c - mean) ** 2 for c in counts) / (n_windows - 1)
           if n_windows > 1 else 0.0)
    dispersion = (var / mean) if mean > 0 else float("nan")
    return {"window_miles": float(window_miles), "n_windows": n_windows,
            "counts": counts, "mean_count": mean, "variance_count": var,
            "dispersion_index": dispersion}


# ----------------------------------------------------------------------- layer

@dataclass
class Layer:
    key: str
    prefix: str
    names: list
    labels: list
    descriptions: list
    rarities: list
    is_unknown: list
    counts: dict
    initial_probs: np.ndarray        # initial-state distribution
    initial_cum: list
    transition_probs: np.ndarray     # permanent transition vector
    transition_cum: list
    duration_means: list             # one configured mean per element
    duration_variances: list         # one configured variance per element
    gamma_shapes: list               # one Gamma shape per element
    gamma_scales: list               # one Gamma scale per element
    construction_mode: str           # generated

    @property
    def n_elements(self) -> int:
        return len(self.names)

    def has_unknown(self) -> bool:
        return any(self.is_unknown)

    def designed_unknown_mass(self) -> float:
        return float(sum(p for p, u in zip(self.initial_probs, self.is_unknown) if u))

    def realized_unknown_mass(self) -> float:
        return float(sum(p for p, u in zip(self.transition_probs, self.is_unknown) if u))

    def sample_initial_index(self, rng) -> int:
        return sample_index_from_cum(self.initial_cum, self.n_elements, rng.random())

    def sample_next_index(self, rng, current, allow_self) -> int:
        return sample_next_index(self.transition_cum, self.n_elements,
                                 rng, current, allow_self)

    def sample_duration(self, rng, element_index, min_duration) -> float:
        return sample_gamma_duration(rng, self.gamma_shapes[element_index],
                                     self.gamma_scales[element_index],
                                     min_duration)


def build_element_duration_parameters(lp: LayerParams, rarities: list,
                                      profiles: dict):
    """Build a distinct Gamma distribution for every element.

    A rarity profile selects the non-overlapping mean band and coefficient of
    variation. Elements are placed deterministically across their band in
    element order, so no additional RNG stream is needed and identities keep
    the same duration law across runs.
    """
    positions = {}
    for rarity in RARITIES:
        members = [i for i, value in enumerate(rarities) if value == rarity]
        for rank, index in enumerate(members):
            unit = 0.0 if len(members) == 1 else 2.0 * rank / (len(members) - 1) - 1.0
            positions[index] = unit

    means, variances, shapes, scales = [], [], [], []
    for index, rarity in enumerate(rarities):
        profile = profiles[rarity]
        mean = (lp.mean_duration * float(profile["mean_multiplier"])
                * (1.0 + float(profile["element_spread"]) * positions[index]))
        cv = float(profile["coefficient_of_variation"])
        variance = (mean * cv) ** 2
        means.append(mean)
        variances.append(variance)
        shapes.append(mean ** 2 / variance)
        scales.append(variance / mean)
    return means, variances, shapes, scales


def build_layer(key, prefix, cfg: SimConfig, rng_element_count, rng_rarity,
                np_rng_transition) -> Layer:
    lp = cfg.layers[key]

    n = rng_element_count.randint(lp.element_count_min, lp.element_count_max)
    counts = assign_rarity_counts(n, cfg.element_class_percentages)
    rarity_list = []
    for rarity in RARITIES:
        rarity_list.extend([rarity] * counts[rarity])
    rng_rarity.shuffle(rarity_list)

    names = [f"{prefix}_{i:03d}" for i in range(n)]
    labels = list(names)
    descriptions = [""] * n

    initial_probs = np.zeros(n, dtype=np.float64)
    class_indices = {}
    for rarity in RARITIES:
        indices = np.array(
            [i for i, value in enumerate(rarity_list) if value == rarity],
            dtype=np.int64)
        class_indices[rarity] = indices
        class_mass = cfg.selection_class_percentages[rarity] / 100.0
        initial_probs[indices] = class_mass / len(indices)

    alpha = cfg.concentration_scale * initial_probs
    raw_transition = np_rng_transition.dirichlet(alpha)
    transition_probs = np.zeros(n, dtype=np.float64)
    for rarity, indices in class_indices.items():
        class_mass = cfg.selection_class_percentages[rarity] / 100.0
        within_class = raw_transition[indices]
        transition_probs[indices] = (
            class_mass * within_class / within_class.sum())
    means, variances, shapes, scales = build_element_duration_parameters(
        lp, rarity_list, cfg.duration_profiles)

    return Layer(key=key, prefix=prefix, names=names, labels=labels,
                 descriptions=descriptions, rarities=rarity_list,
                 is_unknown=[r == "unknown" for r in rarity_list],
                 counts=counts,
                 initial_probs=initial_probs,
                 initial_cum=list(np.cumsum(initial_probs)),
                 transition_probs=transition_probs,
                 transition_cum=list(np.cumsum(transition_probs)),
                 duration_means=means, duration_variances=variances,
                 gamma_shapes=shapes, gamma_scales=scales,
                 construction_mode="generated")


# ------------------------------------------------ conditional transition model

@dataclass(frozen=True)
class ConditionSelector:
    layer_index: int
    element_indices: frozenset
    rarities: frozenset

    def matches(self, current, layers) -> bool:
        element_index = current[self.layer_index]
        return (element_index in self.element_indices
                or layers[self.layer_index].rarities[element_index]
                in self.rarities)


@dataclass(frozen=True)
class ConditionalRule:
    id: str
    target_layer_index: int
    conditions: tuple
    multiplier_vector: np.ndarray
    modifies_unknown: bool

    def matches(self, current, layers) -> bool:
        return all(selector.matches(current, layers)
                   for selector in self.conditions)


@dataclass(frozen=True)
class ConditionalEvaluation:
    probabilities: np.ndarray
    matched_rule_ids: tuple
    influential_rule_ids: tuple
    distribution_modified: bool


class ConditionalTransitionModel:
    """Context-dependent reweighting of permanent layer probabilities.

    Rules are deterministic. They consume no RNG state: the caller performs
    one categorical draw from the returned normalized vector using the
    existing initial-state or transition-sampling stream.
    """

    def __init__(self, cfg: SimConfig, layers):
        self.layers = layers
        self.apply_to_initial_state = bool(
            cfg.transition_model["conditional"]["apply_to_initial_state"])
        self.layer_index = {
            key: index for index, (key, _prefix)
            in enumerate(LAYER_DEFINITIONS)
        }
        self.rules = self._compile_rules(
            cfg.transition_model["conditional"]["rules"])
        self.rules_by_target = [[] for _ in range(N_LAYERS)]
        for rule in self.rules:
            self.rules_by_target[rule.target_layer_index].append(rule)
        self.dependency_order = self._dependency_order()

    def _compile_rules(self, raw_rules):
        compiled = []
        # Sorting by ID makes multiplication and diagnostics independent of
        # the order in which rules appear in YAML.
        for raw in sorted(raw_rules, key=lambda value: value["id"]):
            target_index = self.layer_index[raw["target_layer"]]
            selectors = []
            for layer_key in sorted(
                    raw["when"], key=lambda key: self.layer_index[key]):
                selector = raw["when"][layer_key]
                layer_index = self.layer_index[layer_key]
                layer = self.layers[layer_index]
                element_indices = set()
                for name in selector.get("elements", []):
                    try:
                        element_indices.add(layer.names.index(name))
                    except ValueError as exc:
                        raise ConfigError(
                            f"Conditional rule {raw['id']!r} references "
                            f"unknown element {name!r} in layer "
                            f"{layer_key!r}. Use a valid generated element "
                            "name.") from exc
                selectors.append(ConditionSelector(
                    layer_index=layer_index,
                    element_indices=frozenset(element_indices),
                    rarities=frozenset(selector.get("rarities", [])),
                ))

            target = self.layers[target_index]
            vector = np.ones(target.n_elements, dtype=np.float64)
            for name, multiplier in raw["multipliers"].get(
                    "elements", {}).items():
                try:
                    element_index = target.names.index(name)
                except ValueError as exc:
                    raise ConfigError(
                        f"Conditional rule {raw['id']!r} targets unknown "
                        f"element {name!r} in layer {target.key!r}. "
                        "Use a valid generated element name.") from exc
                vector[element_index] *= float(multiplier)
            for rarity, multiplier in raw["multipliers"].get(
                    "rarities", {}).items():
                for element_index, element_rarity in enumerate(target.rarities):
                    if element_rarity == rarity:
                        vector[element_index] *= float(multiplier)
            modifies_unknown = any(
                target.is_unknown[index] and vector[index] != 1.0
                for index in range(target.n_elements))
            compiled.append(ConditionalRule(
                id=raw["id"],
                target_layer_index=target_index,
                conditions=tuple(selectors),
                multiplier_vector=vector,
                modifies_unknown=modifies_unknown,
            ))
        return tuple(compiled)

    def _dependency_order(self):
        children = [set() for _ in range(N_LAYERS)]
        indegree = [0] * N_LAYERS
        for rule in self.rules:
            child = rule.target_layer_index
            for selector in rule.conditions:
                parent = selector.layer_index
                if child not in children[parent]:
                    children[parent].add(child)
                    indegree[child] += 1
        remaining = set(range(N_LAYERS))
        order = []
        while remaining:
            ready = [index for index in range(N_LAYERS)
                     if index in remaining and indegree[index] == 0]
            if not ready:
                # SimConfig catches this before construction; retain the
                # runtime guard for programmatically mutated configurations.
                raise ConfigError(
                    "Conditional transition dependencies contain a cycle.")
            for parent in ready:
                remaining.remove(parent)
                order.append(parent)
                for child in children[parent]:
                    indegree[child] -= 1
        return tuple(order)

    @staticmethod
    def _normalize(weights, target_layer_key):
        total = float(np.sum(weights))
        if not math.isfinite(total) or total <= 0.0:
            raise ConfigError(
                "Conditional rules leave no valid next element for target "
                f"layer {target_layer_key!r} in the current context.")
        return weights / total

    def evaluate(self, target_layer_index, current_state, base_probabilities,
                 current_element=None, allow_self_transition=True):
        base = np.asarray(base_probabilities, dtype=np.float64)
        baseline = base.copy()
        if current_element is not None and not allow_self_transition:
            baseline[current_element] = 0.0
        baseline = self._normalize(
            baseline, self.layers[target_layer_index].key)

        adjusted = base.copy()
        matched_rules = []
        for rule in self.rules_by_target[target_layer_index]:
            if rule.matches(current_state, self.layers):
                matched_rules.append(rule)
                adjusted *= rule.multiplier_vector
        if current_element is not None and not allow_self_transition:
            adjusted[current_element] = 0.0
        adjusted = self._normalize(
            adjusted, self.layers[target_layer_index].key)
        modified = not np.allclose(
            adjusted, baseline, rtol=1e-14, atol=1e-15)
        influential = []
        if modified:
            for candidate in matched_rules:
                without = base.copy()
                for rule in matched_rules:
                    if rule.id != candidate.id:
                        without *= rule.multiplier_vector
                if current_element is not None and not allow_self_transition:
                    without[current_element] = 0.0
                without = self._normalize(
                    without, self.layers[target_layer_index].key)
                if not np.allclose(
                        adjusted, without, rtol=1e-14, atol=1e-15):
                    influential.append(candidate.id)
        return ConditionalEvaluation(
            probabilities=adjusted,
            matched_rule_ids=tuple(rule.id for rule in matched_rules),
            influential_rule_ids=tuple(influential),
            distribution_modified=modified,
        )

    def probabilities_for(self, target_layer_index, current_state,
                          base_probabilities, current_element=None,
                          allow_self_transition=True):
        return self.evaluate(
            target_layer_index, current_state, base_probabilities,
            current_element=current_element,
            allow_self_transition=allow_self_transition,
        ).probabilities

    def stats_template(self):
        order_names = [LAYER_DEFINITIONS[index][0]
                       for index in self.dependency_order]
        return {
            "mode": "conditional",
            "conditional_initialization": self.apply_to_initial_state,
            "dependency_order": order_names,
            "rules": [{
                "id": rule.id,
                "target_layer":
                    LAYER_DEFINITIONS[rule.target_layer_index][0],
                "modifies_unknown": rule.modifies_unknown,
            } for rule in self.rules],
        }


# -------------------------------------------- exact rare-combination rules (v6)

@dataclass
class CombinationRule:
    """One selected C3-C6 exact combination of rare, known elements."""
    index: int
    items: tuple            # ((layer_idx, element_idx), ...) sorted by layer
    description: str        # "street=constant_lane & ego_maneuver=ego_004"
    source: str             # "selected"
    mass: float             # stationary probability of being matched

    @property
    def size(self) -> int:
        return len(self.items)


def build_exact_rare_combination_rules(cfg: SimConfig, layers, rng_rules) -> list:
    """Select configured numbers of C3-C6 rules uniformly without replacement.

    A rule uses distinct layers, contains one rare element from each selected
    layer, and always contains triggering_conditions. Candidate ordinals are
    sampled from ranges and unranked, so even very large Cartesian products do
    not need to be materialized in memory.
    """
    rare = [[i for i, rarity in enumerate(layer.rarities) if rarity == "rare"]
            for layer in layers]
    missing = [LAYER_DEFINITIONS[k][0] for k, values in enumerate(rare)
               if not values]
    if missing:
        raise ConfigError(
            "Every layer must contain at least one rare element for C3-C6 "
            f"unknown scenarios; missing rare elements in: {missing}.")

    rules = []
    counts = cfg.unknown_scenarios["combination_counts"]
    non_trigger_layers = tuple(range(TRIGGERING_LAYER_INDEX))
    for size in (3, 4, 5, 6):
        groups = []
        population = 0
        for parents in itertools.combinations(non_trigger_layers, size - 1):
            layer_indices = tuple(parents) + (TRIGGERING_LAYER_INDEX,)
            group_count = math.prod(len(rare[k]) for k in layer_indices)
            groups.append((population, population + group_count, layer_indices))
            population += group_count
        requested = counts[size]
        if requested > population:
            raise ConfigError(
                f"unknown_scenarios requests {requested} C{size} rules but "
                f"only {population} eligible rare-element combinations exist.")

        for ordinal in sorted(rng_rules.sample(range(population), requested)):
            start, _end, layer_indices = next(
                group for group in groups if group[0] <= ordinal < group[1])
            local = ordinal - start
            chosen = []
            for k in reversed(layer_indices):
                values = rare[k]
                chosen.append((k, values[local % len(values)]))
                local //= len(values)
            items = tuple(sorted(chosen))
            mass = math.prod(float(layers[k].transition_probs[e])
                             for k, e in items)
            details = " & ".join(
                f"{LAYER_DEFINITIONS[k][0]}={layers[k].names[e]}"
                for k, e in items)
            rules.append(CombinationRule(
                index=len(rules), items=items,
                description=f"C{size}: {details}", source="selected", mass=mass))
    return rules


# ------------------------------------------------------------------- simulation

@dataclass
class Episode:
    """One unknown episode. Types:
      rare_combination - one selected exact C3-C6 rare-element rule persists
    """
    index: int
    layer: str               # layer key | "combination"
    element: str             # element name | rule description | tuple string
    start_time_seconds: float
    start_mileage: float
    end_time_seconds: float = None
    end_mileage: float = None
    truncated: bool = False
    type: str = "rare_combination"

    @property
    def duration_seconds(self) -> float:
        return self.end_time_seconds - self.start_time_seconds

    @property
    def duration_miles(self) -> float:
        return self.end_mileage - self.start_mileage


@dataclass
class SimulationResult:
    total_miles: float
    total_time_seconds: float
    total_events: int
    episodes: list                    # list[Episode], ordered by start
    total_unknown_time_seconds: float  # union of ALL episode intervals
    layer_stats: list
    combination_stats: dict           # v6 exact-rule metadata and counts
    transition_model_stats: dict      # independent/conditional diagnostics
    config: SimConfig

    def episodes_by_type(self) -> dict:
        return {"rare_combination": len(self.episodes)}

    # -- derived outputs -------------------------------------------------------
    def episode_start_miles(self):
        return [e.start_mileage for e in self.episodes]

    def inter_arrival_miles(self):
        """Distance between consecutive episode STARTS (first entry measured
        from the start of the simulation)."""
        out, prev = [], 0.0
        for e in self.episodes:
            out.append(e.start_mileage - prev)
            prev = e.start_mileage
        return out

    def inter_arrival_seconds(self):
        out, prev = [], 0.0
        for e in self.episodes:
            out.append(e.start_time_seconds - prev)
            prev = e.start_time_seconds
        return out

    def window_stats(self):
        """Episode starts per fixed mileage window."""
        return compute_window_stats(self.episode_start_miles(),
                                    self.total_miles,
                                    self.config.mileage_window_miles)

    def episodes_per_million_miles(self) -> float:
        return (len(self.episodes) / (self.total_miles / 1e6)
                if self.total_miles else 0.0)

    def unknown_time_fraction(self) -> float:
        return (self.total_unknown_time_seconds / self.total_time_seconds
                if self.total_time_seconds else 0.0)


class ScenarioSimulator:
    """Event-driven simulator with per-layer unknown-episode tracking."""

    def __init__(self, cfg: SimConfig):
        cfg.validate()
        self.cfg = cfg
        seeds = cfg.seeds
        self.rng_element_count = random.Random(seeds["element_count"])
        self.rng_rarity = random.Random(seeds["rarity_assignment"])
        self.np_rng_transition = np.random.default_rng(seeds["transition_matrix"])
        self.rng_duration = random.Random(seeds["duration"])
        self.rng_initial = random.Random(seeds["initial_state"])
        self.rng_transition = random.Random(seeds["transition_sampling"])
        self.rng_combination_selection = random.Random(
            seeds["combination_selection"])
        self.layers = [build_layer(key, prefix, cfg,
                                   self.rng_element_count,
                                   self.rng_rarity,
                                   self.np_rng_transition)
                       for key, prefix in LAYER_DEFINITIONS]
        self.transition_mode = cfg.transition_model["mode"]
        self.conditional_model = (
            ConditionalTransitionModel(cfg, self.layers)
            if self.transition_mode == "conditional" else None)
        self.unknown_scenarios_enabled = cfg.unknown_scenarios["enabled"]
        if self.unknown_scenarios_enabled:
            self.rules = build_exact_rare_combination_rules(
                cfg, self.layers, self.rng_combination_selection)
        else:
            self.rules = []
        self.rule_index_by_items = {rule.items: rule.index for rule in self.rules}

    def matched_combination_rule(self, current):
        """Return the exact C3-C6 rule matching the current rare set, if any.

        Unknown-rarity elements disqualify a scenario: the new unknown-scenario
        mechanism is deliberately built only from known (common/rare) elements.
        """
        items = []
        for k, element_index in enumerate(current):
            rarity = self.layers[k].rarities[element_index]
            if rarity == "unknown":
                return None
            if rarity == "rare":
                items.append((k, element_index))
        rule_index = self.rule_index_by_items.get(tuple(items))
        return None if rule_index is None else self.rules[rule_index]

    # -- state management -------------------------------------------------------
    def _new_state(self) -> dict:
        layers = self.layers
        selected_by_rarity = [dict.fromkeys(RARITIES, 0) for _ in range(N_LAYERS)]
        visit_counts = [[0] * l.n_elements for l in layers]
        duration_sum = [0.0] * N_LAYERS
        duration_n = [0] * N_LAYERS

        current = [None] * N_LAYERS
        if (self.conditional_model is not None
                and self.conditional_model.apply_to_initial_state):
            initial_order = self.conditional_model.dependency_order
            for k in initial_order:
                evaluation = self.conditional_model.evaluate(
                    k, current, layers[k].initial_probs,
                    current_element=None, allow_self_transition=True)
                cum = np.cumsum(evaluation.probabilities)
                i = sample_index_from_cum(
                    cum, layers[k].n_elements, self.rng_initial.random())
                current[k] = i
        else:
            # Keep the original fixed-order path untouched for independent
            # mode and conditional configurations opting out of conditional
            # initialization.
            for k in range(N_LAYERS):
                current[k] = layers[k].sample_initial_index(self.rng_initial)
        for k in range(N_LAYERS):
            i = current[k]
            selected_by_rarity[k][layers[k].rarities[i]] += 1
            visit_counts[k][i] += 1
        remaining = []
        for k in range(N_LAYERS):
            d = layers[k].sample_duration(self.rng_duration, current[k],
                                          self.cfg.min_duration_seconds)
            duration_sum[k] += d
            duration_n[k] += 1
            remaining.append(d)

        state = {
            "current": current,
            "remaining": remaining,
            "t": 0.0,
            "miles": 0.0,
            "events": 0,
            "episodes": [],                    # closed AND open Episode objects
            "open_combination": None,
            "active_rule_index": None,
            "episodes_opened": 0,
            "episodes_active": 0,
            "union_started_t": 0.0,
            "union_time": 0.0,
            "transitions": [0] * N_LAYERS,
            "unknown_selected": [0] * N_LAYERS,
            "unknown_occupancy_time": [0.0] * N_LAYERS,
            "episodes_by_rule": [0] * len(self.rules),
            "selected_by_rarity": selected_by_rarity,
            "visit_counts": visit_counts,
            "conditional_rule_match_counts": {
                rule.id: 0 for rule in (
                    self.conditional_model.rules
                    if self.conditional_model is not None else ())
            },
            "conditional_rule_influenced_counts": {
                rule.id: 0 for rule in (
                    self.conditional_model.rules
                    if self.conditional_model is not None else ())
            },
            "conditional_influenced_transitions": [0] * N_LAYERS,
            "conditional_matched_context_transitions": [0] * N_LAYERS,
            "conditional_unmatched_context_transitions": [0] * N_LAYERS,
            "conditional_matched_selections": [
                [0] * layer.n_elements for layer in layers],
            "conditional_unmatched_selections": [
                [0] * layer.n_elements for layer in layers],
            "duration_sum": duration_sum,
            "duration_n": duration_n,
            "wall_seconds": 0.0,
        }
        # The v6 route opens only exact C3-C6 rare-element combinations.
        # Unknown-rarity elements are duration/selection classes, not episodes.
        initial_rule = self.matched_combination_rule(current)
        if initial_rule is not None:
            self._open(state, "combination",
                       initial_rule.description, "rare_combination", 0.0, 0.0)
            state["active_rule_index"] = initial_rule.index
            state["episodes_by_rule"][initial_rule.index] += 1
        return state

    # -- generic episode slot management ---------------------------------------
    def _open(self, state, layer_str, element_str, type_str, t, miles):
        ep = Episode(index=state["episodes_opened"], layer=layer_str,
                     element=element_str, start_time_seconds=t,
                     start_mileage=miles, type=type_str)
        state["episodes"].append(ep)
        state["open_combination"] = len(state["episodes"]) - 1
        state["episodes_opened"] += 1
        if state["episodes_active"] == 0:
            state["union_started_t"] = t
        state["episodes_active"] += 1

    def _close(self, state, t, miles, truncated=False):
        ep = state["episodes"][state["open_combination"]]
        ep.end_time_seconds = t
        ep.end_mileage = miles
        ep.truncated = truncated
        state["open_combination"] = None
        state["active_rule_index"] = None
        state["episodes_active"] -= 1
        if state["episodes_active"] == 0:
            state["union_time"] += t - state["union_started_t"]

    # -- main loop --------------------------------------------------------------
    def run(self, progress_every_miles=None, log=None) -> SimulationResult:
        result, _state = self.run_resumable(
            state=None, wall_limit_seconds=None,
            progress_every_miles=progress_every_miles, log=log)
        return result

    def run_resumable(self, state=None, wall_limit_seconds=None,
                      progress_every_miles=None, log=None):
        """Event-driven loop; returns (result, state) at target time or
        (None, state) when the wall limit is hit (checkpoint + resume is
        bit-identical to an uninterrupted run)."""
        wall_start = time.monotonic()
        deadline = (None if wall_limit_seconds is None
                    else wall_start + wall_limit_seconds)
        if state is None:
            state = self._new_state()

        cfg = self.cfg
        layers = self.layers
        min_dur = cfg.min_duration_seconds
        mph = cfg.average_speed_mph
        target_time = cfg.target_time_seconds
        allow_self = cfg.allow_self_transition

        unk_l = [l.is_unknown for l in layers]
        rar_l = [l.rarities for l in layers]
        cum_l = [l.transition_cum for l in layers]
        n_l = [l.n_elements for l in layers]
        shape_l = [l.gamma_shapes for l in layers]
        scale_l = [l.gamma_scales for l in layers]
        trans_rng = self.rng_transition
        gamma = self.rng_duration.gammavariate
        layer_range = tuple(range(N_LAYERS))
        conditional_model = self.conditional_model
        conditional_enabled = conditional_model is not None
        conditional_order = (
            conditional_model.dependency_order if conditional_enabled
            else layer_range)

        current = state["current"]
        remaining = state["remaining"]
        t = state["t"]
        miles = state["miles"]
        events = state["events"]
        transitions = state["transitions"]
        unknown_selected = state["unknown_selected"]
        selected_by_rarity = state["selected_by_rarity"]
        visit_counts = state["visit_counts"]
        duration_sum = state["duration_sum"]
        duration_n = state["duration_n"]
        unknown_occupancy_time = state["unknown_occupancy_time"]
        conditional_rule_match_counts = state[
            "conditional_rule_match_counts"]
        conditional_rule_influenced_counts = state[
            "conditional_rule_influenced_counts"]
        conditional_influenced_transitions = state[
            "conditional_influenced_transitions"]
        conditional_matched_context_transitions = state[
            "conditional_matched_context_transitions"]
        conditional_unmatched_context_transitions = state[
            "conditional_unmatched_context_transitions"]
        conditional_matched_selections = state[
            "conditional_matched_selections"]
        conditional_unmatched_selections = state[
            "conditional_unmatched_selections"]

        def sample_dur(k, element_index):
            d = gamma(shape_l[k][element_index], scale_l[k][element_index])
            if d < min_dur:
                d = min_dur
            duration_sum[k] += d
            duration_n[k] += 1
            return d

        if progress_every_miles:
            next_progress = (math.floor(miles / progress_every_miles) + 1) \
                * progress_every_miles
        else:
            next_progress = math.inf

        while t < target_time:
            if deadline is not None and (events & 0xFFF) == 0 \
                    and time.monotonic() >= deadline:
                break
            # jump to the next layer expiry
            dt = min(min(remaining), target_time - t)
            t += dt
            miles += mph * dt / 3600.0
            expired = []
            for k in layer_range:
                if unk_l[k][current[k]]:
                    unknown_occupancy_time[k] += dt
                r = remaining[k] - dt
                remaining[k] = r
                if r <= 1e-12:
                    expired.append(k)
            # Stop exactly at the configured time, truncating the current
            # sojourns rather than overshooting to the next event boundary.
            if t >= target_time - 1e-9:
                break
            changed = False
            if conditional_enabled:
                expired_set = set(expired)
                expired_order = [k for k in conditional_order
                                 if k in expired_set]
            else:
                # This is the original path and preserves independent-mode
                # iteration and RNG consumption exactly.
                expired_order = expired
            for k in expired_order:
                cur = current[k]
                matched_context = False
                if conditional_enabled:
                    evaluation = conditional_model.evaluate(
                        k, current, layers[k].transition_probs,
                        current_element=cur,
                        allow_self_transition=allow_self)
                    nxt = sample_index_from_cum(
                        np.cumsum(evaluation.probabilities), n_l[k],
                        trans_rng.random())
                    matched_context = bool(evaluation.matched_rule_ids)
                    if matched_context:
                        conditional_matched_context_transitions[k] += 1
                        for rule_id in evaluation.matched_rule_ids:
                            conditional_rule_match_counts[rule_id] += 1
                    else:
                        conditional_unmatched_context_transitions[k] += 1
                    if evaluation.distribution_modified:
                        conditional_influenced_transitions[k] += 1
                        for rule_id in evaluation.influential_rule_ids:
                            conditional_rule_influenced_counts[rule_id] += 1
                else:
                    nxt = sample_next_index(cum_l[k], n_l[k], trans_rng, cur,
                                            allow_self)
                nxt_u = unk_l[k][nxt]
                if nxt != cur:
                    changed = True
                current[k] = nxt
                remaining[k] = sample_dur(k, nxt)
                transitions[k] += 1
                selected_by_rarity[k][rar_l[k][nxt]] += 1
                visit_counts[k][nxt] += 1
                if conditional_enabled:
                    selection_counts = (
                        conditional_matched_selections
                        if matched_context
                        else conditional_unmatched_selections)
                    selection_counts[k][nxt] += 1
                if nxt_u:
                    unknown_selected[k] += 1
            # ---- exact C3-C6 rare-combination episode -----------------------
            if changed and self.unknown_scenarios_enabled:
                open_index = state["active_rule_index"]
                matched_rule = self.matched_combination_rule(current)
                matched_index = (None if matched_rule is None
                                 else matched_rule.index)
                if open_index is not None and open_index != matched_index:
                    self._close(state, t, miles)
                if matched_index is not None and open_index != matched_index:
                    self._open(state, "combination",
                               matched_rule.description, "rare_combination",
                               t, miles)
                    state["active_rule_index"] = matched_index
                    state["episodes_by_rule"][matched_index] += 1
            events += 1

            if miles >= next_progress:
                if log:
                    log(f"progress: {miles:12,.0f} mi | {t:14,.0f} s | "
                        f"{events:12,} events | "
                          f"{state['episodes_opened']:9,} rare-combination episodes")
                next_progress += progress_every_miles

        state["t"] = t
        state["miles"] = miles
        state["events"] = events
        state["wall_seconds"] += time.monotonic() - wall_start

        if t < target_time - 1e-9:
            return None, state

        if state["open_combination"] is not None:
            self._close(state, t, miles, truncated=True)

        return self._build_result(state), state

    def _build_result(self, state) -> SimulationResult:
        cfg = self.cfg
        layer_stats = []
        for k, (key, _prefix) in enumerate(LAYER_DEFINITIONS):
            layer = self.layers[k]
            n_trans = state["transitions"][k]
            n_dur = state["duration_n"][k]
            visit_counts = list(state["visit_counts"][k])
            total_visits = sum(visit_counts)
            element_metadata = [{
                "id": element_id,
                "label": layer.labels[index],
                "description": layer.descriptions[index],
                "rarity": layer.rarities[index],
                "duration_distribution": "gamma",
                "duration_mean_seconds": layer.duration_means[index],
                "duration_variance_seconds2": layer.duration_variances[index],
                "duration_gamma_shape": layer.gamma_shapes[index],
                "duration_gamma_scale": layer.gamma_scales[index],
                "visit_count": visit_counts[index],
                "realized_selection_rate":
                    (visit_counts[index] / total_visits) if total_visits else 0.0,
            } for index, element_id in enumerate(layer.names)]
            layer_stats.append({
                "layer": key,
                "n_elements": layer.n_elements,
                "construction_mode": layer.construction_mode,
                "has_unknown": layer.has_unknown(),
                "counts": dict(layer.counts),
                "element_proportions": {
                    rarity: layer.counts[rarity] / layer.n_elements
                    for rarity in RARITIES
                },
                "configured_selection_class_percentages": {
                    rarity: float(cfg.selection_class_percentages[rarity])
                    for rarity in RARITIES
                },
                "transition_class_proportions": {
                    rarity: float(sum(
                        probability for probability, element_rarity
                        in zip(layer.transition_probs, layer.rarities)
                        if element_rarity == rarity))
                    for rarity in RARITIES
                },
                "designed_unknown_mass": layer.designed_unknown_mass(),
                "realized_unknown_mass": layer.realized_unknown_mass(),
                "baseline_unknown_mass": layer.realized_unknown_mass(),
                "empirical_unknown_occupancy":
                    (state["unknown_occupancy_time"][k] / state["t"])
                    if state["t"] else 0.0,
                "transitions": n_trans,
                "unknown_selected": state["unknown_selected"][k],
                "empirical_unknown_rate":
                    (state["unknown_selected"][k] / n_trans) if n_trans else 0.0,
                "conditional_selection_rate":
                    (state["unknown_selected"][k] / n_trans)
                    if n_trans else 0.0,
                "episodes": 0,
                "selected_by_rarity": dict(state["selected_by_rarity"][k]),
                "visit_counts": visit_counts,
                "element_names": list(layer.names),
                "element_labels": list(layer.labels),
                "element_descriptions": list(layer.descriptions),
                "elements": element_metadata,
                "transition_probs": [float(p) for p in layer.transition_probs],
                "mean_duration_config": (
                    sum(layer.duration_means) / len(layer.duration_means)),
                "duration_profiles": dict(cfg.duration_profiles),
                "mean_duration_empirical":
                    (state["duration_sum"][k] / n_dur) if n_dur else 0.0,
            })

        combination_stats = {
            "enabled": self.unknown_scenarios_enabled,
            "mechanism": "exact_rare_element_combinations",
            "require_triggering_condition": True,
            "exact_rare_set": True,
            "combination_counts": dict(
                cfg.unknown_scenarios["combination_counts"]),
            "episodes": sum(state["episodes_by_rule"]),
            "episodes_by_size": {
                size: sum(state["episodes_by_rule"][r.index]
                          for r in self.rules if r.size == size)
                for size in (3, 4, 5, 6)
            },
            "rules": [{
                "index": r.index, "description": r.description,
                "size": r.size, "items": [
                    {"layer": LAYER_DEFINITIONS[k][0],
                     "element": self.layers[k].names[e]}
                    for k, e in r.items],
                "source": r.source, "mass": r.mass,
                "episodes": state["episodes_by_rule"][r.index],
            } for r in self.rules],
        }
        transition_stats = self._build_transition_model_stats(state)
        return SimulationResult(
            total_miles=state["miles"],
            total_time_seconds=state["t"],
            total_events=state["events"],
            episodes=state["episodes"],
            total_unknown_time_seconds=state["union_time"],
            layer_stats=layer_stats,
            combination_stats=combination_stats,
            transition_model_stats=transition_stats,
            config=cfg,
        )

    def _build_transition_model_stats(self, state):
        if self.conditional_model is None:
            dormant_rules = self.cfg.transition_model[
                "conditional"].get("rules", [])
            return {
                "mode": "independent",
                "conditional_initialization": False,
                "dependency_order": [
                    key for key, _prefix in LAYER_DEFINITIONS],
                "rules": [{
                    "id": rule["id"],
                    "target_layer": rule["target_layer"],
                    "active": False,
                    "match_count": 0,
                    "influenced_transition_count": 0,
                } for rule in sorted(
                    dormant_rules, key=lambda value: value["id"])],
                "layers": [],
            }

        template = self.conditional_model.stats_template()
        match_counts = state["conditional_rule_match_counts"]
        rule_influenced_counts = state[
            "conditional_rule_influenced_counts"]
        influenced = state["conditional_influenced_transitions"]
        for rule_stats in template["rules"]:
            rule_stats.update({
                "active": True,
                "match_count": match_counts[rule_stats["id"]],
                "influenced_transition_count":
                    rule_influenced_counts[rule_stats["id"]],
            })
        layer_rows = []
        for k, (key, _prefix) in enumerate(LAYER_DEFINITIONS):
            layer = self.layers[k]

            def nonzero_counts(values):
                return {
                    name: count for name, count
                    in zip(layer.names, values) if count
                }

            n_trans = state["transitions"][k]
            layer_rows.append({
                "layer": key,
                "matched_context_transitions":
                    state["conditional_matched_context_transitions"][k],
                "unmatched_context_transitions":
                    state["conditional_unmatched_context_transitions"][k],
                "influenced_transitions": influenced[k],
                "selections_under_matched_context": nonzero_counts(
                    state["conditional_matched_selections"][k]),
                "selections_under_unmatched_context": nonzero_counts(
                    state["conditional_unmatched_selections"][k]),
                "baseline_unknown_mass": layer.realized_unknown_mass(),
                "empirical_unknown_occupancy":
                    (state["unknown_occupancy_time"][k] / state["t"])
                    if state["t"] else 0.0,
                "conditional_unknown_selection_rate":
                    (state["unknown_selected"][k] / n_trans)
                    if n_trans else 0.0,
            })
        template["layers"] = layer_rows
        return template
