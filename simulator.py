"""
Layered scenario model with event-driven simulation and unknown-episode
duration measurement.

Six independent layers (street, temporal modifications, ego maneuver,
RU maneuver, environmental conditions, triggering conditions):

  - street: FIXED list of 12 real route-composition elements whose exact
    probabilities form the permanent transition vector (no Dirichlet, no
    unknown elements).
  - environmental_conditions: sampled elements, but NO unknown elements
    (known rarity proportions renormalized).
  - remaining layers: element count sampled uniformly from a per-layer
    [min, max] range; rarity categories assigned by largest-remainder in
    configurable proportions and shuffled; rarity-based weights with a
    "calculated" or "fixed" unknown weight (always below very_rare); ONE
    permanent transition vector per layer sampled from
    Dirichlet(concentration_scale * normalized_weights) at initialization.

Durations: Gamma per layer (shape = mean^2/var, scale = var/mean), clamped
to min_duration_seconds. Event-driven main loop advances to the next layer
expiry and converts time to mileage with a constant average speed.

UNKNOWN-EPISODE SEMANTICS (replaces per-tuple encounter counting):
  1. An episode starts when a layer transitions from a known element to an
     unknown element (also at t=0 if a layer's initial element is unknown).
  2. It ends when that same layer transitions from that unknown element to
     a known element.
  3. A direct hop to a DIFFERENT unknown element closes the episode and
     opens a new one at the same instant.
  4. A self-transition onto the SAME unknown element continues the episode.
  5. Episodes are per layer and may overlap; overlapping episodes are
     separate counts with independent durations.
  6. Changes in other layers never start or end an episode.
  7. Episodes still open at the end of the simulation are closed at final
     time and flagged truncated.

Unknown COMBINATIONS (re-enabled, v3) - two mechanisms, both episodic:
  - HASH combinations: when the scenario tuple changes and contains only
    known elements, the SHA-256 classifier may flag it; the episode lasts
    exactly as long as that tuple persists (any element change ends it;
    self-transitions continue it).
  - PATTERN combinations (SOTIF-style interactions): configured rules are
    conjunctions over >=2 layers, e.g. street=forced_merge_merging AND
    environmental_conditions=environment_003. A rule's episode starts when
    all its elements are simultaneously current and ends when any of them
    leaves - naturally spanning many changes of unrelated layers. Rules
    are manual (config) and/or generated once from the pattern_rules seed,
    accumulating rules until a target stationary mass is reached. Rules
    may only reference known-rarity elements.
All three episode types (element / pattern / hash_combination) are tracked
concurrently and independently; the union unknown time merges overlaps.

Reproducibility: one configurable seed per random source (config `seeds`);
the same config produces identical results, including across
checkpoint/resume.
"""

from __future__ import annotations

import bisect
import hashlib
import math
import random
import time
from dataclasses import dataclass, field

import numpy as np
import yaml

RARITIES = ("common", "medium", "rare", "very_rare", "unknown")
KNOWN_RARITIES = ("common", "medium", "rare", "very_rare")

SEED_KEYS = ("element_count", "rarity_assignment", "transition_matrix",
             "duration", "initial_state", "transition_sampling",
             "pattern_rules")

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


class ConfigError(ValueError):
    """Invalid or inconsistent configuration."""


# ---------------------------------------------------------------- configuration

@dataclass
class LayerParams:
    mean_duration: float                 # seconds
    variance_duration: float             # seconds^2
    element_count_min: int = None        # sampled layers only
    element_count_max: int = None
    allow_unknown: bool = True           # sampled layers only
    fixed_elements: list = None          # [{name, probability}, ...] -> fixed layer

    @property
    def is_fixed(self) -> bool:
        return self.fixed_elements is not None


def _default_seeds():
    return {"element_count": 12345, "rarity_assignment": 23456,
            "transition_matrix": 34567, "duration": 45678,
            "initial_state": 56789, "transition_sampling": 67890,
            "pattern_rules": 78901}


def _default_proportions():
    return {"common": 0.50, "medium": 0.25, "rare": 0.10,
            "very_rare": 0.05, "unknown": 0.10}


def _default_base_weights():
    return {"common": 1.0, "medium": 0.4, "rare": 0.1, "very_rare": 0.03}


@dataclass
class SimConfig:
    seeds: dict = field(default_factory=_default_seeds)
    global_seed: int = 42
    target_total_miles: float = 2_000_000.0
    average_speed_mph: float = 50.0
    min_duration_seconds: float = 1.0
    mileage_window_miles: float = 10_000.0
    enable_unknown_combinations: bool = True    # hash + pattern combinations
    combination_rules: dict = field(default_factory=lambda: {
        "manual": [], "generated_max_rules": 0,
        "generated_layers_per_rule": 2, "generated_target_mass": 0.0})
    rarity_proportions: dict = field(default_factory=_default_proportions)
    base_weights: dict = field(default_factory=_default_base_weights)
    unknown_weight_mode: str = "calculated"
    target_unknown_element_probability: float = 0.004
    fixed_unknown_weight: float = 0.001
    unknown_combination_probability: float = 0.005  # dormant classifier parameter
    concentration_scale: float = 20_000.0   # from concentration_study.md
    allow_self_transition: bool = True
    layers: dict = field(default_factory=dict)   # layer key -> LayerParams

    # -- construction --------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str) -> "SimConfig":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return cls.from_dict(raw)

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
    def effective_proportions(self, lp: LayerParams) -> dict:
        """Rarity proportions for a sampled layer. Layers with
        allow_unknown=false use the four known proportions renormalized to
        sum to 1 (unknown share removed)."""
        props = dict(self.rarity_proportions)
        if not lp.allow_unknown:
            known_total = sum(props[r] for r in KNOWN_RARITIES)
            return {**{r: props[r] / known_total for r in KNOWN_RARITIES},
                    "unknown": 0.0}
        return props

    # -- validation -----------------------------------------------------------
    def validate(self) -> None:
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

        cr = self.combination_rules
        if not isinstance(cr, dict):
            raise ConfigError("combination_rules must be a mapping.")
        allowed = {"manual", "generated_max_rules",
                   "generated_layers_per_rule", "generated_target_mass"}
        bad = [k for k in cr if k not in allowed]
        if bad:
            raise ConfigError(f"combination_rules has unknown keys: {bad}")
        cr.setdefault("manual", [])
        cr.setdefault("generated_max_rules", 0)
        cr.setdefault("generated_layers_per_rule", 2)
        cr.setdefault("generated_target_mass", 0.0)
        layer_keys = {key for key, _ in LAYER_DEFINITIONS}
        for i, rule in enumerate(cr["manual"]):
            if not isinstance(rule, dict) or len(rule) < 2:
                raise ConfigError(
                    f"combination_rules.manual[{i}] must be a mapping of at "
                    "least TWO layer->element entries (a combination is an "
                    "interaction between layers).")
            unknown = [k for k in rule if k not in layer_keys]
            if unknown:
                raise ConfigError(
                    f"combination_rules.manual[{i}] has unknown layers: "
                    f"{unknown}")
        if not (2 <= int(cr["generated_layers_per_rule"]) <= N_LAYERS):
            raise ConfigError(
                "generated_layers_per_rule must be between 2 and 6.")
        if cr["generated_target_mass"] < 0 or cr["generated_max_rules"] < 0:
            raise ConfigError("generated_target_mass and generated_max_rules "
                              "must be non-negative.")

        if self.unknown_weight_mode not in ("calculated", "fixed"):
            raise ConfigError("unknown_weight_mode must be 'calculated' or "
                              f"'fixed', got {self.unknown_weight_mode!r}")

        missing = [r for r in RARITIES if r not in self.rarity_proportions]
        if missing:
            raise ConfigError(f"rarity_proportions missing categories: {missing}")
        if any(self.rarity_proportions[r] < 0 for r in RARITIES):
            raise ConfigError("rarity_proportions must be non-negative.")
        total = sum(self.rarity_proportions[r] for r in RARITIES)
        if abs(total - 1.0) > 1e-6:
            raise ConfigError(f"rarity_proportions must sum to 1.0 (got {total}).")

        for r in KNOWN_RARITIES:
            if r not in self.base_weights:
                raise ConfigError(f"base_weights missing category: {r}")
            if self.base_weights[r] <= 0:
                raise ConfigError(f"base_weights[{r}] must be positive.")
        if "unknown" in self.base_weights:
            raise ConfigError("Do not set base_weights['unknown'].")

        if not (0 < self.target_unknown_element_probability < 1):
            raise ConfigError("target_unknown_element_probability must be in (0,1).")
        if not (0 <= self.unknown_combination_probability < 1):
            raise ConfigError("unknown_combination_probability must be in [0,1).")
        if self.fixed_unknown_weight <= 0:
            raise ConfigError("fixed_unknown_weight must be positive.")
        if self.average_speed_mph <= 0:
            raise ConfigError("average_speed_mph must be positive.")
        if self.target_total_miles <= 0:
            raise ConfigError("target_total_miles must be positive.")
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
            if lp.is_fixed:
                self._validate_fixed_elements(key, lp)
            else:
                if lp.element_count_min is None or lp.element_count_max is None:
                    raise ConfigError(
                        f"Layer '{key}': needs element_count_min/max "
                        "(or fixed_elements).")
                if not (0 < lp.element_count_min <= lp.element_count_max):
                    raise ConfigError(
                        f"Layer '{key}': require 0 < element_count_min <= "
                        "element_count_max.")
                if lp.allow_unknown:
                    # every n in the range must (a) yield >= 1 unknown
                    # element and (b) admit a valid unknown weight
                    # (smaller than very_rare) under the configured mode
                    props = self.effective_proportions(lp)
                    for n in range(lp.element_count_min,
                                   lp.element_count_max + 1):
                        counts = assign_rarity_counts(n, props)
                        if counts["unknown"] == 0:
                            raise ConfigError(
                                f"Layer '{key}': element count n={n} in the "
                                "configured range yields zero unknown "
                                "elements; shrink the range, raise the "
                                "unknown proportion, or set "
                                "allow_unknown: false.")
                        try:
                            compute_unknown_weight(counts, self)
                        except ConfigError as exc:
                            raise ConfigError(
                                f"Layer '{key}': element count n={n} in the "
                                f"configured range is infeasible: {exc}"
                            ) from exc

        extra = [k for k in self.layers
                 if k not in [key for key, _ in LAYER_DEFINITIONS]]
        if extra:
            raise ConfigError(f"Unknown layer keys in config: {extra}")

    @staticmethod
    def _validate_fixed_elements(key, lp: LayerParams):
        elems = lp.fixed_elements
        if not isinstance(elems, list) or not elems:
            raise ConfigError(f"Layer '{key}': fixed_elements must be a "
                              "non-empty list.")
        names, probs = [], []
        for e in elems:
            if not isinstance(e, dict) or "name" not in e or "probability" not in e:
                raise ConfigError(f"Layer '{key}': each fixed element needs "
                                  "'name' and 'probability'.")
            names.append(str(e["name"]))
            probs.append(float(e["probability"]))
        if len(set(names)) != len(names):
            raise ConfigError(f"Layer '{key}': fixed element names must be unique.")
        if any(p <= 0 for p in probs):
            raise ConfigError(f"Layer '{key}': fixed probabilities must be > 0.")
        if abs(sum(probs) - 1.0) > 1e-6:
            raise ConfigError(f"Layer '{key}': fixed probabilities must sum "
                              f"to 1.0 (got {sum(probs)}).")
        if lp.allow_unknown:
            raise ConfigError(f"Layer '{key}': fixed_elements layers contain "
                              "no unknown elements; set allow_unknown: false.")


# ------------------------------------------------------- rarity / weight helpers

def assign_rarity_counts(n_elements: int, proportions: dict) -> dict:
    """Largest-remainder integer counts per rarity category (sum == n)."""
    exact = {r: n_elements * proportions[r] for r in RARITIES}
    counts = {r: math.floor(exact[r]) for r in RARITIES}
    remainder = n_elements - sum(counts.values())
    by_fraction = sorted(RARITIES, key=lambda r: -(exact[r] - counts[r]))
    for r in by_fraction[:remainder]:
        counts[r] += 1
    return counts


def compute_unknown_weight(counts: dict, cfg: SimConfig) -> float:
    """Unknown-element transition weight for one layer (see README).
    Only called for layers that actually contain unknown elements."""
    very_rare_w = cfg.base_weights["very_rare"]

    if cfg.unknown_weight_mode == "fixed":
        w = cfg.fixed_unknown_weight
        if not (w < very_rare_w):
            raise ConfigError(
                f"fixed_unknown_weight ({w}) must be smaller than the "
                f"very_rare weight ({very_rare_w}).")
        return w

    n_unknown = counts["unknown"]
    if n_unknown == 0:
        raise ConfigError(
            "unknown_weight_mode='calculated' requires at least one unknown "
            "element in the layer. Increase rarity_proportions['unknown'] or "
            "use unknown_weight_mode='fixed'.")
    p = cfg.target_unknown_element_probability
    known_mass = sum(counts[r] * cfg.base_weights[r] for r in KNOWN_RARITIES)
    w = p * known_mass / (n_unknown * (1.0 - p))
    if not (w < very_rare_w):
        raise ConfigError(
            f"Calculated unknown weight ({w:.6g}) is not smaller than the "
            f"very_rare weight ({very_rare_w}). Fix this by one of: "
            "(1) increase the proportion of unknown elements, "
            "(2) lower target_unknown_element_probability, or "
            "(3) use unknown_weight_mode='fixed'.")
    return w


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
    rarities: list
    is_unknown: list
    counts: dict
    unknown_weight: float            # None for layers without unknown elements
    initial_probs: np.ndarray        # initial-state distribution
    initial_cum: list
    transition_probs: np.ndarray     # permanent transition vector
    transition_cum: list
    gamma_shape: float
    gamma_scale: float
    is_fixed: bool                   # fixed element list (street)

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

    def sample_duration(self, rng, min_duration) -> float:
        return sample_gamma_duration(rng, self.gamma_shape, self.gamma_scale,
                                     min_duration)


def _cosmetic_rarity(probability: float) -> str:
    """Reporting-only rarity label for fixed-list elements (no unknowns)."""
    if probability >= 0.10:
        return "common"
    if probability >= 0.03:
        return "medium"
    if probability >= 0.01:
        return "rare"
    return "very_rare"


def build_layer(key, prefix, cfg: SimConfig, rng_element_count, rng_rarity,
                np_rng_transition) -> Layer:
    lp = cfg.layers[key]
    shape = lp.mean_duration ** 2 / lp.variance_duration
    scale = lp.variance_duration / lp.mean_duration

    if lp.is_fixed:
        # Fixed real elements: the given probabilities ARE the permanent
        # transition vector (no Dirichlet draw, no RNG consumption) and the
        # initial-state distribution. All elements are known.
        names = [str(e["name"]) for e in lp.fixed_elements]
        probs = np.array([float(e["probability"]) for e in lp.fixed_elements])
        probs = probs / probs.sum()   # exact within float tolerance
        rarities = [_cosmetic_rarity(p) for p in probs]
        counts = {r: rarities.count(r) for r in RARITIES}
        return Layer(key=key, prefix=prefix, names=names, rarities=rarities,
                     is_unknown=[False] * len(names), counts=counts,
                     unknown_weight=None,
                     initial_probs=probs, initial_cum=list(np.cumsum(probs)),
                     transition_probs=probs,
                     transition_cum=list(np.cumsum(probs)),
                     gamma_shape=shape, gamma_scale=scale, is_fixed=True)

    n = rng_element_count.randint(lp.element_count_min, lp.element_count_max)
    props = cfg.effective_proportions(lp)
    counts = assign_rarity_counts(n, props)
    rarity_list = []
    for r in RARITIES:
        rarity_list.extend([r] * counts[r])
    rng_rarity.shuffle(rarity_list)

    names = [f"{prefix}_{i:03d}" for i in range(n)]
    weight_of = dict(cfg.base_weights)
    unknown_w = None
    if counts["unknown"] > 0:
        unknown_w = compute_unknown_weight(counts, cfg)
        weight_of["unknown"] = unknown_w

    w = np.array([weight_of[r] for r in rarity_list], dtype=float)
    initial_probs = w / w.sum()
    alpha = cfg.concentration_scale * initial_probs
    transition_probs = np_rng_transition.dirichlet(alpha)
    transition_probs = transition_probs / transition_probs.sum()

    return Layer(key=key, prefix=prefix, names=names, rarities=rarity_list,
                 is_unknown=[r == "unknown" for r in rarity_list],
                 counts=counts, unknown_weight=unknown_w,
                 initial_probs=initial_probs,
                 initial_cum=list(np.cumsum(initial_probs)),
                 transition_probs=transition_probs,
                 transition_cum=list(np.cumsum(transition_probs)),
                 gamma_shape=shape, gamma_scale=scale, is_fixed=False)


# ------------------------------------------------- unknown-combination classifier
# NOTE: temporarily unused (enable_unknown_combinations=false). Kept intact,
# with its global_seed semantics, for later reintroduction within the episode
# framework (open question: a combination-episode would be the lifetime of
# that exact tuple).

class UnknownCombinationClassifier:
    """Deterministic SHA-256 unknown-combination membership test.

    hash_value = int(sha256("<global_seed>|<name1>|...|<name6>")) / 2**256;
    unknown iff hash_value < unknown_combination_probability. Stable across
    runs (unlike Python's built-in hash()), seeded, O(1), nothing stored."""

    _TWO_256 = 2 ** 256

    def __init__(self, global_seed: int, unknown_combination_probability: float):
        self.global_seed = global_seed
        self.threshold = float(unknown_combination_probability)
        self.prefix = f"{global_seed}|".encode("utf-8")

    def hash_value(self, element_names) -> float:
        payload = self.prefix + "|".join(element_names).encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest, "big") / self._TWO_256

    def is_unknown_combination(self, element_names) -> bool:
        return self.hash_value(element_names) < self.threshold


# ----------------------------------------------------- pattern combination rules

@dataclass
class CombinationRule:
    """A pattern-based unknown combination: a conjunction of specific
    known-rarity elements in >=2 layers (wildcards everywhere else).
    Matched <=> every (layer, element) pair is simultaneously current."""
    index: int
    items: tuple            # ((layer_idx, element_idx), ...) sorted by layer
    description: str        # "street=constant_lane & ego_maneuver=ego_004"
    source: str             # "manual" | "generated"
    mass: float             # stationary probability of being matched

    def matched(self, current) -> bool:
        return all(current[k] == e for k, e in self.items)


def build_combination_rules(cfg: SimConfig, layers, rng_rules) -> list:
    """Manual rules from the config plus rules generated once from the
    pattern_rules seed: random distinct layers, one KNOWN element each
    (uniform), accumulated until generated_target_mass stationary mass is
    reached or generated_max_rules is hit. Duplicate rules are skipped;
    unknown-rarity elements are rejected (combinations are interactions of
    known elements)."""
    cr = cfg.combination_rules
    key_to_idx = {key: k for k, (key, _) in enumerate(LAYER_DEFINITIONS)}
    rules, seen = [], set()

    def add(items, source):
        items = tuple(sorted(items))
        if items in seen:
            return False
        for k, e in items:
            if layers[k].is_unknown[e]:
                raise ConfigError(
                    f"Combination rule references the unknown-rarity element "
                    f"'{layers[k].names[e]}' in layer "
                    f"'{LAYER_DEFINITIONS[k][0]}'; rules must use known "
                    "elements (pick a different element).")
        mass = 1.0
        for k, e in items:
            mass *= float(layers[k].transition_probs[e])
        desc = " & ".join(f"{LAYER_DEFINITIONS[k][0]}={layers[k].names[e]}"
                          for k, e in items)
        rules.append(CombinationRule(index=len(rules), items=items,
                                     description=desc, source=source,
                                     mass=mass))
        seen.add(items)
        return True

    for rule in cr["manual"]:
        items = []
        for layer_key, element_name in rule.items():
            k = key_to_idx[layer_key]
            try:
                e = layers[k].names.index(str(element_name))
            except ValueError:
                raise ConfigError(
                    f"Combination rule element '{element_name}' does not "
                    f"exist in layer '{layer_key}' "
                    f"(valid: {layers[k].names[:5]}...).") from None
            items.append((k, e))
        add(items, "manual")

    target = float(cr["generated_target_mass"])
    max_rules = int(cr["generated_max_rules"])
    per_rule = int(cr["generated_layers_per_rule"])
    generated_mass = 0.0
    attempts = 0
    while (generated_mass < target and
           sum(1 for r in rules if r.source == "generated") < max_rules and
           attempts < 10000):
        attempts += 1
        ks = rng_rules.sample(range(N_LAYERS), per_rule)
        items = []
        ok = True
        for k in ks:
            known = [i for i in range(layers[k].n_elements)
                     if not layers[k].is_unknown[i]]
            if not known:
                ok = False
                break
            items.append((k, rng_rules.choice(known)))
        if not ok:
            continue
        before = len(rules)
        add(items, "generated")
        if len(rules) > before:
            generated_mass += rules[-1].mass
    return rules


# ------------------------------------------------------------------- simulation

@dataclass
class Episode:
    """One unknown episode. Types:
      element          - a layer occupies an unknown element (rules 1-4)
      pattern          - a combination rule is continuously matched
      hash_combination - an all-known tuple flagged by the SHA-256
                         classifier persists (any element change ends it)
    """
    index: int
    layer: str               # layer key | "combination"
    element: str             # element name | rule description | tuple string
    start_time_seconds: float
    start_mileage: float
    end_time_seconds: float = None
    end_mileage: float = None
    truncated: bool = False
    type: str = "element"    # "element" | "pattern" | "hash_combination"

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
    combination_stats: dict           # rules, masses, per-rule/hash counts
    config: SimConfig

    def episodes_by_type(self) -> dict:
        out = {"element": 0, "pattern": 0, "hash_combination": 0}
        for e in self.episodes:
            out[e.type] += 1
        return out

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
        self.rng_pattern_rules = random.Random(seeds["pattern_rules"])
        self.layers = [build_layer(key, prefix, cfg,
                                   self.rng_element_count,
                                   self.rng_rarity,
                                   self.np_rng_transition)
                       for key, prefix in LAYER_DEFINITIONS]
        self.classifier = UnknownCombinationClassifier(
            cfg.global_seed, cfg.unknown_combination_probability)
        if cfg.enable_unknown_combinations:
            self.rules = build_combination_rules(cfg, self.layers,
                                                 self.rng_pattern_rules)
        else:
            self.rules = []
        # layer index -> rules referencing it (for incremental re-evaluation)
        self.rules_by_layer = [[] for _ in range(N_LAYERS)]
        for rule in self.rules:
            for k, _e in rule.items:
                self.rules_by_layer[k].append(rule.index)

    def scenario_names(self, idx_tuple):
        return tuple(self.layers[k].names[idx_tuple[k]] for k in range(N_LAYERS))

    def scenario_string(self, idx_tuple) -> str:
        return "|".join(self.scenario_names(idx_tuple))

    # -- state management -------------------------------------------------------
    def _new_state(self) -> dict:
        layers = self.layers
        selected_by_rarity = [dict.fromkeys(RARITIES, 0) for _ in range(N_LAYERS)]
        visit_counts = [[0] * l.n_elements for l in layers]
        duration_sum = [0.0] * N_LAYERS
        duration_n = [0] * N_LAYERS

        current = []
        for k in range(N_LAYERS):
            i = layers[k].sample_initial_index(self.rng_initial)
            current.append(i)
            selected_by_rarity[k][layers[k].rarities[i]] += 1
            visit_counts[k][i] += 1
        remaining = []
        for k in range(N_LAYERS):
            d = layers[k].sample_duration(self.rng_duration,
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
            "open_element": [None] * N_LAYERS,   # per-layer episode index
            "open_pattern": [None] * len(self.rules),   # per-rule
            "open_hash": None,
            "episodes_opened": 0,
            "episodes_active": 0,              # all types (union tracking)
            "element_unknown_active": 0,       # element episodes only (hash gate)
            "union_started_t": 0.0,
            "union_time": 0.0,
            "transitions": [0] * N_LAYERS,
            "unknown_selected": [0] * N_LAYERS,
            "episodes_by_layer": [0] * N_LAYERS,       # element episodes
            "episodes_by_rule": [0] * len(self.rules),  # pattern episodes
            "hash_episode_count": 0,
            "selected_by_rarity": selected_by_rarity,
            "visit_counts": visit_counts,
            "duration_sum": duration_sum,
            "duration_n": duration_n,
            "wall_seconds": 0.0,
        }
        # t=0 starts: element episodes for layers on unknown elements, then
        # pattern episodes for initially matched rules, then a hash episode
        # if the initial all-known tuple is flagged.
        for k in range(N_LAYERS):
            if layers[k].is_unknown[current[k]]:
                self._open(state, ("element", k),
                           LAYER_DEFINITIONS[k][0],
                           layers[k].names[current[k]], "element", 0.0, 0.0)
                state["element_unknown_active"] += 1
                state["episodes_by_layer"][k] += 1
        for rule in self.rules:
            if rule.matched(current):
                self._open(state, ("pattern", rule.index), "combination",
                           rule.description, "pattern", 0.0, 0.0)
                state["episodes_by_rule"][rule.index] += 1
        if (self.cfg.enable_unknown_combinations
                and state["element_unknown_active"] == 0
                and self.classifier.is_unknown_combination(
                    self.scenario_names(tuple(current)))):
            self._open(state, ("hash",), "combination",
                       self.scenario_string(tuple(current)),
                       "hash_combination", 0.0, 0.0)
            state["hash_episode_count"] += 1
        return state

    # -- generic episode slot management ---------------------------------------
    def _slot_get(self, state, slot):
        if slot[0] == "element":
            return state["open_element"][slot[1]]
        if slot[0] == "pattern":
            return state["open_pattern"][slot[1]]
        return state["open_hash"]

    def _slot_set(self, state, slot, value):
        if slot[0] == "element":
            state["open_element"][slot[1]] = value
        elif slot[0] == "pattern":
            state["open_pattern"][slot[1]] = value
        else:
            state["open_hash"] = value

    def _open(self, state, slot, layer_str, element_str, type_str, t, miles):
        ep = Episode(index=state["episodes_opened"], layer=layer_str,
                     element=element_str, start_time_seconds=t,
                     start_mileage=miles, type=type_str)
        state["episodes"].append(ep)
        self._slot_set(state, slot, len(state["episodes"]) - 1)
        state["episodes_opened"] += 1
        if state["episodes_active"] == 0:
            state["union_started_t"] = t
        state["episodes_active"] += 1

    def _close(self, state, slot, t, miles, truncated=False):
        ep = state["episodes"][self._slot_get(state, slot)]
        ep.end_time_seconds = t
        ep.end_mileage = miles
        ep.truncated = truncated
        self._slot_set(state, slot, None)
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
        """Event-driven loop; returns (result, state) at target mileage or
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
        target = cfg.target_total_miles
        allow_self = cfg.allow_self_transition

        unk_l = [l.is_unknown for l in layers]
        rar_l = [l.rarities for l in layers]
        cum_l = [l.transition_cum for l in layers]
        n_l = [l.n_elements for l in layers]
        shape_l = [l.gamma_shape for l in layers]
        scale_l = [l.gamma_scale for l in layers]
        trans_rng = self.rng_transition
        gamma = self.rng_duration.gammavariate
        layer_range = tuple(range(N_LAYERS))
        names_l = [l.names for l in layers]
        layer_keys = [key for key, _ in LAYER_DEFINITIONS]
        combos_enabled = cfg.enable_unknown_combinations
        rules = self.rules
        rules_by_layer = self.rules_by_layer
        sha256 = hashlib.sha256
        hash_prefix = self.classifier.prefix
        threshold = self.classifier.threshold
        two256 = 2 ** 256
        changed_layers = []
        affected = set()

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

        def sample_dur(k):
            d = gamma(shape_l[k], scale_l[k])
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

        while miles < target:
            if deadline is not None and (events & 0xFFF) == 0 \
                    and time.monotonic() >= deadline:
                break
            # jump to the next layer expiry
            dt = min(remaining)
            t += dt
            miles += mph * dt / 3600.0
            expired = []
            for k in layer_range:
                r = remaining[k] - dt
                remaining[k] = r
                if r <= 1e-12:
                    expired.append(k)
            changed = False
            for k in expired:
                cur = current[k]
                nxt = sample_next_index(cum_l[k], n_l[k], trans_rng, cur,
                                        allow_self)
                cur_u = unk_l[k][cur]
                nxt_u = unk_l[k][nxt]
                # element-episode rules 1-4 (per layer)
                if cur_u:
                    if nxt != cur:
                        if nxt_u:                       # rule 3: restart
                            self._close(state, ("element", k), t, miles)
                            self._open(state, ("element", k), layer_keys[k],
                                       names_l[k][nxt], "element", t, miles)
                            state["episodes_by_layer"][k] += 1
                        else:                           # rule 2: end
                            self._close(state, ("element", k), t, miles)
                            state["element_unknown_active"] -= 1
                    # else rule 4: same unknown element continues
                elif nxt_u:                             # rule 1: start
                    self._open(state, ("element", k), layer_keys[k],
                               names_l[k][nxt], "element", t, miles)
                    state["element_unknown_active"] += 1
                    state["episodes_by_layer"][k] += 1
                if nxt != cur:
                    changed = True
                    changed_layers.append(k)
                current[k] = nxt
                remaining[k] = sample_dur(k)
                transitions[k] += 1
                selected_by_rarity[k][rar_l[k][nxt]] += 1
                visit_counts[k][nxt] += 1
                if nxt_u:
                    unknown_selected[k] += 1
            # ---- combination episodes: evaluated once per event, after all
            # expired layers were updated (self-transitions change nothing) --
            if changed and combos_enabled:
                # pattern rules referencing a changed layer
                affected.clear()
                for k in changed_layers:
                    affected.update(rules_by_layer[k])
                for ri in sorted(affected):
                    rule = rules[ri]
                    now = rule.matched(current)
                    is_open = state["open_pattern"][ri] is not None
                    if now and not is_open:
                        self._open(state, ("pattern", ri), "combination",
                                   rule.description, "pattern", t, miles)
                        state["episodes_by_rule"][ri] += 1
                    elif is_open and not now:
                        self._close(state, ("pattern", ri), t, miles)
                # hash episode: the previous tuple no longer exists
                if state["open_hash"] is not None:
                    self._close(state, ("hash",), t, miles)
                if state["element_unknown_active"] == 0:
                    names_str = "|".join([names_l[k][current[k]]
                                          for k in layer_range])
                    payload = hash_prefix + names_str.encode()
                    hv = int.from_bytes(sha256(payload).digest(), "big") / two256
                    if hv < threshold:
                        self._open(state, ("hash",), "combination",
                                   names_str, "hash_combination", t, miles)
                        state["hash_episode_count"] += 1
            changed_layers.clear()
            events += 1

            if miles >= next_progress:
                if log:
                    log(f"progress: {miles:12,.0f} mi | {t:14,.0f} s | "
                        f"{events:12,} events | "
                        f"{state['episodes_opened']:9,} episodes (all types)")
                next_progress += progress_every_miles

        state["t"] = t
        state["miles"] = miles
        state["events"] = events
        state["wall_seconds"] += time.monotonic() - wall_start

        if miles < target:
            return None, state

        # rule 7: close still-open episodes (all types) at final time
        for k in layer_range:
            if state["open_element"][k] is not None:
                self._close(state, ("element", k), t, miles, truncated=True)
        for ri in range(len(self.rules)):
            if state["open_pattern"][ri] is not None:
                self._close(state, ("pattern", ri), t, miles, truncated=True)
        if state["open_hash"] is not None:
            self._close(state, ("hash",), t, miles, truncated=True)

        return self._build_result(state), state

    def _build_result(self, state) -> SimulationResult:
        cfg = self.cfg
        layer_stats = []
        for k, (key, _prefix) in enumerate(LAYER_DEFINITIONS):
            layer = self.layers[k]
            n_trans = state["transitions"][k]
            n_dur = state["duration_n"][k]
            layer_stats.append({
                "layer": key,
                "n_elements": layer.n_elements,
                "is_fixed": layer.is_fixed,
                "has_unknown": layer.has_unknown(),
                "counts": dict(layer.counts),
                "unknown_weight": layer.unknown_weight,
                "designed_unknown_mass": layer.designed_unknown_mass(),
                "realized_unknown_mass": layer.realized_unknown_mass(),
                "transitions": n_trans,
                "unknown_selected": state["unknown_selected"][k],
                "empirical_unknown_rate":
                    (state["unknown_selected"][k] / n_trans) if n_trans else 0.0,
                "episodes": state["episodes_by_layer"][k],
                "selected_by_rarity": dict(state["selected_by_rarity"][k]),
                "visit_counts": list(state["visit_counts"][k]),
                "element_names": list(layer.names),
                "transition_probs": [float(p) for p in layer.transition_probs],
                "mean_duration_config": cfg.layers[key].mean_duration,
                "mean_duration_empirical":
                    (state["duration_sum"][k] / n_dur) if n_dur else 0.0,
            })

        combination_stats = {
            "enabled": cfg.enable_unknown_combinations,
            "hash_threshold": cfg.unknown_combination_probability,
            "hash_episodes": state["hash_episode_count"],
            "pattern_episodes": sum(state["episodes_by_rule"]),
            "rules": [{
                "index": r.index, "description": r.description,
                "source": r.source, "mass": r.mass,
                "episodes": state["episodes_by_rule"][r.index],
            } for r in self.rules],
        }
        return SimulationResult(
            total_miles=state["miles"],
            total_time_seconds=state["t"],
            total_events=state["events"],
            episodes=state["episodes"],
            total_unknown_time_seconds=state["union_time"],
            layer_stats=layer_stats,
            combination_stats=combination_stats,
            config=cfg,
        )
