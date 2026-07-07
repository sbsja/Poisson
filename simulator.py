"""
Layered scenario model with event-driven simulation.

Six independent layers (street, temporal modifications, ego maneuver,
RU maneuver, environmental conditions, triggering conditions), each with:
  - 50-100 elements (sampled uniformly), rarity categories assigned in
    configurable proportions and randomly shuffled across elements
  - rarity-based transition weights; unknown weight via "calculated" or
    "fixed" mode (must always be smaller than the very_rare weight)
  - ONE fixed transition probability vector per layer, Dirichlet-sampled
    once at initialization (alpha = concentration_scale * normalized
    weights) and never resampled during simulation
  - Gamma-distributed element durations (per-layer mean/variance,
    clamped to min_duration_seconds)

A scenario tuple is the ordered combination of the six current elements.
A scenario is unknown if:
  1. at least one element has rarity category "unknown", OR
  2. all elements are known but the combination is classified unknown by a
     deterministic SHA-256 hash test (seeded, thresholded, not enumerated).

The simulation is event-driven: it jumps to the next time at which at least
one layer changes, and runs until a target mileage is reached, converting
elapsed seconds to miles with a constant configurable average speed.
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
    mean_duration: float       # seconds
    variance_duration: float   # seconds^2


def _default_proportions():
    return {"common": 0.50, "medium": 0.25, "rare": 0.10,
            "very_rare": 0.05, "unknown": 0.10}


def _default_base_weights():
    return {"common": 1.0, "medium": 0.4, "rare": 0.1, "very_rare": 0.03}


@dataclass
class SimConfig:
    simulation_seed: int = 12345
    global_seed: int = 42
    target_total_miles: float = 2_000_000.0
    average_speed_mph: float = 50.0
    min_duration_seconds: float = 1.0
    count_initial_scenario: bool = True
    element_count_min: int = 50
    element_count_max: int = 100
    rarity_proportions: dict = field(default_factory=_default_proportions)
    base_weights: dict = field(default_factory=_default_base_weights)
    unknown_weight_mode: str = "calculated"
    target_unknown_element_probability: float = 0.004
    fixed_unknown_weight: float = 0.001
    unknown_combination_probability: float = 0.005
    concentration_scale: float = 100.0
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
            raise ConfigError("Config must define 'layers' with per-layer "
                              "mean_duration and variance_duration.")
        try:
            cfg.layers = {k: LayerParams(**v) for k, v in layers_raw.items()}
        except TypeError as exc:
            raise ConfigError(f"Bad layer duration config: {exc}") from exc
        cfg.validate()
        return cfg

    # -- validation -----------------------------------------------------------
    def validate(self) -> None:
        if self.unknown_weight_mode not in ("calculated", "fixed"):
            raise ConfigError("unknown_weight_mode must be 'calculated' or 'fixed', "
                              f"got {self.unknown_weight_mode!r}")
        if not (0 < self.element_count_min <= self.element_count_max):
            raise ConfigError("Require 0 < element_count_min <= element_count_max.")

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
            raise ConfigError("Do not set base_weights['unknown']; the unknown "
                              "weight is controlled by unknown_weight_mode.")

        if not (0 < self.target_unknown_element_probability < 1):
            raise ConfigError("target_unknown_element_probability must be in (0, 1).")
        if not (0 <= self.unknown_combination_probability < 1):
            raise ConfigError("unknown_combination_probability must be in [0, 1).")
        if self.fixed_unknown_weight <= 0:
            raise ConfigError("fixed_unknown_weight must be positive.")
        if self.average_speed_mph <= 0:
            raise ConfigError("average_speed_mph must be positive.")
        if self.target_total_miles <= 0:
            raise ConfigError("target_total_miles must be positive.")
        if self.min_duration_seconds <= 0:
            raise ConfigError("min_duration_seconds must be positive "
                              "(durations must always be positive).")
        if self.concentration_scale <= 0:
            raise ConfigError("concentration_scale must be positive.")

        for key, _prefix in LAYER_DEFINITIONS:
            if key not in self.layers:
                raise ConfigError(f"Missing duration parameters for layer '{key}'.")
            lp = self.layers[key]
            if lp.mean_duration <= 0 or lp.variance_duration <= 0:
                raise ConfigError(f"Layer '{key}': mean_duration and "
                                  "variance_duration must be positive.")


# ------------------------------------------------------- rarity / weight helpers

def assign_rarity_counts(n_elements: int, proportions: dict) -> dict:
    """Integer rarity counts for a layer via the largest-remainder method.

    Counts always sum exactly to n_elements and each count differs from the
    exact proportional value by less than 1.
    """
    exact = {r: n_elements * proportions[r] for r in RARITIES}
    counts = {r: math.floor(exact[r]) for r in RARITIES}
    remainder = n_elements - sum(counts.values())
    by_fraction = sorted(RARITIES, key=lambda r: -(exact[r] - counts[r]))
    for r in by_fraction[:remainder]:
        counts[r] += 1
    return counts


def compute_unknown_weight(counts: dict, cfg: SimConfig) -> float:
    """Unknown-element transition weight for one layer.

    "fixed" mode: return cfg.fixed_unknown_weight.
    "calculated" mode: solve for the weight w such that the layer's total
    unknown probability mass equals target_unknown_element_probability p:

        n_unknown * w / (known_mass + n_unknown * w) = p
        =>  w = p * known_mass / (n_unknown * (1 - p))

    In both modes the result must be smaller than the very_rare weight.
    """
    very_rare_w = cfg.base_weights["very_rare"]

    if cfg.unknown_weight_mode == "fixed":
        w = cfg.fixed_unknown_weight
        if not (w < very_rare_w):
            raise ConfigError(
                f"fixed_unknown_weight ({w}) must be smaller than the "
                f"very_rare weight ({very_rare_w}). Lower fixed_unknown_weight.")
        return w

    # calculated mode
    n_unknown = counts["unknown"]
    if n_unknown == 0:
        raise ConfigError(
            "unknown_weight_mode='calculated' requires at least one unknown "
            "element per layer. Increase rarity_proportions['unknown'] or use "
            "unknown_weight_mode='fixed'.")
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
    """Categorical sample: index i with cum[i-1] <= u < cum[i]."""
    i = bisect.bisect_right(cum, u)
    return i if i < n else n - 1


def sample_next_index(cum, n, rng, current, allow_self):
    """Sample the next element index from a fixed cumulative probability
    vector. If self-transitions are disabled, rejection-sample until the
    result differs from the current element (exactly equivalent to
    renormalizing with the current element excluded)."""
    for _ in range(1_000_000):
        i = sample_index_from_cum(cum, n, rng.random())
        if allow_self or i != current:
            return i
    raise RuntimeError("Self-transition rejection sampling failed; the "
                       "transition vector is too concentrated on one element.")


def sample_gamma_duration(rng, shape, scale, min_duration):
    """Gamma-distributed duration in seconds, clamped to min_duration."""
    d = rng.gammavariate(shape, scale)
    return d if d > min_duration else min_duration


# ----------------------------------------------------------------------- layer

@dataclass
class Layer:
    key: str
    prefix: str
    names: list                  # element name per index, e.g. "street_012"
    rarities: list               # rarity category per index
    is_unknown: list             # bool per index
    counts: dict                 # rarity -> count
    unknown_weight: float
    element_weights: np.ndarray  # designed rarity weight per element
    initial_probs: np.ndarray    # normalized designed weights (initial sampling)
    initial_cum: list
    transition_probs: np.ndarray  # fixed Dirichlet-sampled vector (never resampled)
    transition_cum: list
    gamma_shape: float
    gamma_scale: float

    @property
    def n_elements(self) -> int:
        return len(self.names)

    def designed_unknown_mass(self) -> float:
        """Unknown probability mass of the designed (pre-Dirichlet) weights."""
        return float(sum(p for p, u in zip(self.initial_probs, self.is_unknown) if u))

    def realized_unknown_mass(self) -> float:
        """Unknown probability mass of the stored Dirichlet-sampled vector."""
        return float(sum(p for p, u in zip(self.transition_probs, self.is_unknown) if u))

    def rarity_mass(self, probs) -> dict:
        out = dict.fromkeys(RARITIES, 0.0)
        for p, r in zip(probs, self.rarities):
            out[r] += float(p)
        return out

    def sample_initial_index(self, rng) -> int:
        """Initial element via the rarity-weighted element probabilities."""
        return sample_index_from_cum(self.initial_cum, self.n_elements, rng.random())

    def sample_next_index(self, rng, current, allow_self) -> int:
        return sample_next_index(self.transition_cum, self.n_elements,
                                 rng, current, allow_self)

    def sample_duration(self, rng, min_duration) -> float:
        return sample_gamma_duration(rng, self.gamma_shape, self.gamma_scale,
                                     min_duration)


def build_layer(key: str, prefix: str, cfg: SimConfig,
                py_rng: random.Random, np_rng: np.random.Generator) -> Layer:
    """Build one layer: element count, rarity assignment, weights, fixed
    Dirichlet transition vector, and Gamma duration parameters."""
    n = py_rng.randint(cfg.element_count_min, cfg.element_count_max)  # inclusive
    counts = assign_rarity_counts(n, cfg.rarity_proportions)

    rarity_list = []
    for r in RARITIES:
        rarity_list.extend([r] * counts[r])
    py_rng.shuffle(rarity_list)  # random shuffle of category assignments

    names = [f"{prefix}_{i:03d}" for i in range(n)]
    unknown_w = compute_unknown_weight(counts, cfg)
    weight_of = dict(cfg.base_weights)
    weight_of["unknown"] = unknown_w

    w = np.array([weight_of[r] for r in rarity_list], dtype=float)
    initial_probs = w / w.sum()

    # Fixed transition probabilities: Dirichlet sampled ONCE, stored permanently.
    alpha = cfg.concentration_scale * initial_probs
    transition_probs = np_rng.dirichlet(alpha)
    transition_probs = transition_probs / transition_probs.sum()  # numerical safety

    lp = cfg.layers[key]
    shape = lp.mean_duration ** 2 / lp.variance_duration
    scale = lp.variance_duration / lp.mean_duration

    return Layer(
        key=key, prefix=prefix, names=names, rarities=rarity_list,
        is_unknown=[r == "unknown" for r in rarity_list],
        counts=counts, unknown_weight=unknown_w,
        element_weights=w, initial_probs=initial_probs,
        initial_cum=list(np.cumsum(initial_probs)),
        transition_probs=transition_probs,
        transition_cum=list(np.cumsum(transition_probs)),
        gamma_shape=shape, gamma_scale=scale,
    )


# ------------------------------------------------- unknown-combination classifier

class UnknownCombinationClassifier:
    """Deterministic hash-based unknown-combination membership test.

    A scenario tuple of known-element names is serialized as
    "<global_seed>|street_012|temporal_004|ego_031|ru_008|environment_022|trigger_003",
    hashed with SHA-256, converted to an integer, normalized into [0, 1) by
    dividing by 2**256, and classified unknown iff the value is below
    unknown_combination_probability. Nothing is stored or enumerated; the
    same tuple and seed always give the same result (hashlib.sha256 is
    stable across runs, unlike Python's built-in hash()).
    """

    _TWO_256 = 2 ** 256

    def __init__(self, global_seed: int, unknown_combination_probability: float):
        self.global_seed = global_seed
        self.threshold = float(unknown_combination_probability)
        self.prefix = f"{global_seed}|".encode("utf-8")

    def hash_value(self, element_names) -> float:
        """Normalized SHA-256 hash of the seeded scenario string, in [0, 1)."""
        payload = self.prefix + "|".join(element_names).encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest, "big") / self._TWO_256

    def is_unknown_combination(self, element_names) -> bool:
        return self.hash_value(element_names) < self.threshold


# ------------------------------------------------------------------- simulation

@dataclass
class Encounter:
    index: int
    time_seconds: float
    mileage: float
    reason: str      # "unknown_element" | "unknown_combination"
    scenario: str    # e.g. "street_012|temporal_004|ego_031|ru_008|environment_022|trigger_003"


@dataclass
class SimulationResult:
    total_miles: float
    total_time_seconds: float
    total_events: int
    total_tuple_changes: int
    known_tuple_changes: int          # changes into tuples with no unknown element
    encounters: list                  # list[Encounter]
    layer_stats: list                 # per-layer dict of statistics
    config: SimConfig

    def inter_arrival_miles(self) -> list:
        """Distance between consecutive encounters; the first entry is the
        distance from the start of the simulation to the first encounter."""
        out, prev = [], 0.0
        for e in self.encounters:
            out.append(e.mileage - prev)
            prev = e.mileage
        return out


class ScenarioSimulator:
    """Event-driven simulator over the 6-layer scenario model."""

    def __init__(self, cfg: SimConfig):
        cfg.validate()
        self.cfg = cfg
        self.py_rng = random.Random(cfg.simulation_seed)      # hot-loop RNG
        self.np_rng = np.random.default_rng(cfg.simulation_seed)  # Dirichlet RNG
        self.layers = [build_layer(key, prefix, cfg, self.py_rng, self.np_rng)
                       for key, prefix in LAYER_DEFINITIONS]
        self.classifier = UnknownCombinationClassifier(
            cfg.global_seed, cfg.unknown_combination_probability)

    # -- scenario classification ----------------------------------------------
    def scenario_names(self, idx_tuple):
        return tuple(self.layers[k].names[idx_tuple[k]] for k in range(N_LAYERS))

    def scenario_string(self, idx_tuple) -> str:
        return "|".join(self.scenario_names(idx_tuple))

    def classify_scenario(self, idx_tuple):
        """(is_unknown, reason) for a tuple of element indices.

        Rule 1: any element with rarity 'unknown' -> unknown scenario.
        Rule 2: all-known tuple in the hash-defined unknown-combination set.
        """
        for k in range(N_LAYERS):
            if self.layers[k].is_unknown[idx_tuple[k]]:
                return True, "unknown_element"
        if self.classifier.is_unknown_combination(self.scenario_names(idx_tuple)):
            return True, "unknown_combination"
        return False, None

    @staticmethod
    def check_new_scenario(prev_tuple, new_tuple, classify_fn):
        """Unknown-encounter counting rule: an encounter is counted only when
        the simulator ENTERS a DIFFERENT scenario tuple that is unknown.
        Remaining in the same (unknown) tuple never counts again."""
        if new_tuple == prev_tuple:
            return False, None
        return classify_fn(new_tuple)

    # -- state management -------------------------------------------------------
    def _new_state(self) -> dict:
        """Initialize the simulation state: one initial element per layer
        (sampled from the rarity-weighted element probabilities) plus one
        initial Gamma duration per selected element."""
        rng = self.py_rng
        layers = self.layers
        selected_by_rarity = [dict.fromkeys(RARITIES, 0) for _ in range(N_LAYERS)]
        duration_sum = [0.0] * N_LAYERS
        duration_n = [0] * N_LAYERS

        current = []
        for k in range(N_LAYERS):
            i = layers[k].sample_initial_index(rng)
            current.append(i)
            selected_by_rarity[k][layers[k].rarities[i]] += 1
        remaining = []
        for k in range(N_LAYERS):
            d = layers[k].sample_duration(rng, self.cfg.min_duration_seconds)
            duration_sum[k] += d
            duration_n[k] += 1
            remaining.append(d)

        state = {
            "current": current,                 # current element index per layer
            "remaining": remaining,             # remaining duration (s) per layer
            "t": 0.0,                           # simulation time (s)
            "miles": 0.0,                       # simulated mileage
            "prev_tuple": tuple(current),       # previous scenario tuple
            "unknown_active": sum(1 for k in range(N_LAYERS)
                                  if layers[k].is_unknown[current[k]]),
            "encounters": [],
            "events": 0,
            "tuple_changes": 0,
            "known_changes": 0,
            "transitions": [0] * N_LAYERS,
            "unknown_selected": [0] * N_LAYERS,
            "selected_by_rarity": selected_by_rarity,
            "duration_sum": duration_sum,
            "duration_n": duration_n,
            "wall_seconds": 0.0,
        }
        # The initial scenario is the combination of the six selected elements;
        # entering it counts as entering a new scenario tuple (configurable).
        if self.cfg.count_initial_scenario:
            is_unk, reason = self.classify_scenario(state["prev_tuple"])
            if is_unk:
                state["encounters"].append(Encounter(
                    0, 0.0, 0.0, reason, self.scenario_string(state["prev_tuple"])))
        return state

    # -- main loop --------------------------------------------------------------
    def run(self, progress_every_miles=None, log=None) -> SimulationResult:
        """Run to the target mileage in one go and return the result."""
        result, _state = self.run_resumable(
            state=None, wall_limit_seconds=None,
            progress_every_miles=progress_every_miles, log=log)
        return result

    def run_resumable(self, state=None, wall_limit_seconds=None,
                      progress_every_miles=None, log=None):
        """Event-driven simulation with optional wall-clock chunking.

        Returns (SimulationResult, state) when the target mileage is reached,
        or (None, state) if wall_limit_seconds elapsed first; in that case the
        returned state (together with this simulator object, which carries the
        RNG state) can be checkpointed and passed back in to resume with
        bit-identical results.
        """
        wall_start = time.monotonic()
        deadline = (None if wall_limit_seconds is None
                    else wall_start + wall_limit_seconds)
        if state is None:
            state = self._new_state()

        cfg = self.cfg
        rng = self.py_rng
        layers = self.layers
        min_dur = cfg.min_duration_seconds
        mph = cfg.average_speed_mph
        target = cfg.target_total_miles
        allow_self = cfg.allow_self_transition

        # local bindings for the hot loop
        names_l = [l.names for l in layers]
        unk_l = [l.is_unknown for l in layers]
        rar_l = [l.rarities for l in layers]
        cum_l = [l.transition_cum for l in layers]
        n_l = [l.n_elements for l in layers]
        shape_l = [l.gamma_shape for l in layers]
        scale_l = [l.gamma_scale for l in layers]
        gamma = rng.gammavariate
        sha256 = hashlib.sha256
        hash_prefix = self.classifier.prefix
        threshold = self.classifier.threshold
        two256 = 2 ** 256
        layer_range = tuple(range(N_LAYERS))

        # unpack state
        current = state["current"]
        remaining = state["remaining"]
        t = state["t"]
        miles = state["miles"]
        prev_tuple = state["prev_tuple"]
        unknown_active = state["unknown_active"]
        encounters = state["encounters"]
        events = state["events"]
        tuple_changes = state["tuple_changes"]
        known_changes = state["known_changes"]
        transitions = state["transitions"]
        unknown_selected = state["unknown_selected"]
        selected_by_rarity = state["selected_by_rarity"]
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

        # ---- event-driven loop ----
        while miles < target:
            # wall-clock chunking check (coarse, every 4096 events)
            if deadline is not None and (events & 0xFFF) == 0 \
                    and time.monotonic() >= deadline:
                break
            # 1-2. smallest remaining duration across layers = time step
            dt = min(remaining)
            # 3. advance time
            t += dt
            # 4-5. convert to distance and advance mileage
            miles += mph * dt / 3600.0
            # 6-7. subtract dt everywhere; find expired layers
            expired = []
            for k in layer_range:
                r = remaining[k] - dt
                remaining[k] = r
                if r <= 1e-12:
                    expired.append(k)
            # 8. update ALL expired layers first (transition + new duration)
            for k in expired:
                cur = current[k]
                nxt = sample_next_index(cum_l[k], n_l[k], rng, cur, allow_self)
                if unk_l[k][nxt] != unk_l[k][cur]:
                    unknown_active += 1 if unk_l[k][nxt] else -1
                current[k] = nxt
                remaining[k] = sample_dur(k)
                transitions[k] += 1
                selected_by_rarity[k][rar_l[k][nxt]] += 1
                if unk_l[k][nxt]:
                    unknown_selected[k] += 1
            # 9-13. ONE scenario tuple + ONE unknown check per event
            new_tuple = tuple(current)
            if new_tuple != prev_tuple:
                tuple_changes += 1
                if unknown_active:
                    encounters.append(Encounter(
                        len(encounters), t, miles, "unknown_element",
                        "|".join([names_l[k][new_tuple[k]] for k in layer_range])))
                else:
                    known_changes += 1
                    names_str = "|".join([names_l[k][new_tuple[k]]
                                          for k in layer_range])
                    payload = hash_prefix + names_str.encode()
                    hash_value = int.from_bytes(sha256(payload).digest(), "big") / two256
                    if hash_value < threshold:
                        encounters.append(Encounter(
                            len(encounters), t, miles,
                            "unknown_combination", names_str))
                prev_tuple = new_tuple
            events += 1

            if miles >= next_progress:
                if log:
                    log(f"progress: {miles:12,.0f} mi | {t:14,.0f} s | "
                        f"{events:12,} events | {len(encounters):9,} encounters")
                next_progress += progress_every_miles

        # repack scalar state (lists were mutated in place)
        state["t"] = t
        state["miles"] = miles
        state["prev_tuple"] = prev_tuple
        state["unknown_active"] = unknown_active
        state["events"] = events
        state["tuple_changes"] = tuple_changes
        state["known_changes"] = known_changes
        state["wall_seconds"] += time.monotonic() - wall_start

        if miles < target:          # wall limit hit; caller may checkpoint+resume
            return None, state
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
                "counts": dict(layer.counts),
                "unknown_weight": layer.unknown_weight,
                "designed_unknown_mass": layer.designed_unknown_mass(),
                "realized_unknown_mass": layer.realized_unknown_mass(),
                "transitions": n_trans,
                "unknown_selected": state["unknown_selected"][k],
                "empirical_unknown_rate":
                    (state["unknown_selected"][k] / n_trans) if n_trans else 0.0,
                "selected_by_rarity": dict(state["selected_by_rarity"][k]),
                "mean_duration_config": cfg.layers[key].mean_duration,
                "mean_duration_empirical":
                    (state["duration_sum"][k] / n_dur) if n_dur else 0.0,
            })

        return SimulationResult(
            total_miles=state["miles"],
            total_time_seconds=state["t"],
            total_events=state["events"],
            total_tuple_changes=state["tuple_changes"],
            known_tuple_changes=state["known_changes"],
            encounters=state["encounters"],
            layer_stats=layer_stats,
            config=cfg,
        )
