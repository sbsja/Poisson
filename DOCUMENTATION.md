# Technical Documentation — Layered Scenario Model Simulator

This document explains exactly how every part of the program works,
component by component, in the order data flows through the system.
File references: `simulator.py` (core), `run_simulation.py` (runner),
`config.yaml` (parameters), `test_simulator.py` (tests).

---

## 1. Big picture

```
config.yaml
    │  SimConfig.from_yaml()  →  validation
    ▼
ScenarioSimulator.__init__()
    │  6 independent RNG streams (one per random source)
    │  build_layer() ×6:
    │     element count → rarity counts → shuffle → unknown weight
    │     → weight vector → normalize → Dirichlet draw (ONCE)
    │     → cumulative arrays, Gamma shape/scale
    │  UnknownCombinationClassifier(global_seed, threshold)
    ▼
run() / run_resumable()
    │  _new_state(): initial element + initial duration per layer
    │  event-driven loop until target mileage:
    │     jump to next expiry → advance time & miles → transition
    │     expired layers → ONE tuple → ONE unknown check → record
    ▼
SimulationResult
    │  encounters (mileage, time, reason, scenario)
    │  inter_arrival_miles(), inter_arrival_seconds(), window_stats()
    ▼
run_simulation.py → encounters.csv, windows.csv, summary.md,
                    stats.json, plots/*.png
```

The six layers, in fixed tuple order (constant `LAYER_DEFINITIONS`):

| # | config key | element prefix |
|---|---|---|
| 0 | street | `street_` |
| 1 | temporal_modifications | `temporal_` |
| 2 | ego_maneuver | `ego_` |
| 3 | ru_maneuver | `ru_` |
| 4 | environmental_conditions | `environment_` |
| 5 | triggering_conditions | `trigger_` |

Layers are fully independent: there are no conditional probabilities
between layers, and each layer has its own transition probability vector.

---

## 2. Configuration (`SimConfig`)

`SimConfig.from_yaml(path)` reads the YAML into a dict and delegates to
`SimConfig.from_dict(raw)`, which:

1. Pops the `layers` sub-dict and converts each entry into a `LayerParams`
   dataclass (`mean_duration`, `variance_duration`).
2. Constructs the `SimConfig` dataclass from the remaining keys. Unknown
   keys raise `ConfigError` (a subclass of `ValueError`), so typos fail
   loudly instead of being silently ignored.
3. Calls `validate()`.

`validate()` enforces, among others: the `seeds` mapping contains exactly
the six required entries and all are integers; `unknown_weight_mode` is
`"calculated"` or `"fixed"`; rarity proportions cover all five categories,
are non-negative and sum to 1.0 (tolerance 1e-6); base weights exist and
are positive for the four known categories; `base_weights['unknown']` must
NOT be set (the unknown weight is derived, see §5); probabilities lie in
their valid ranges; speed, target mileage, `min_duration_seconds`,
`concentration_scale`, `mileage_window_miles` are positive; and every one
of the six layers has positive mean and variance durations.

Every tunable named in the assignment lives in this file: rarity
proportions, base weights, `unknown_weight_mode`,
`target_unknown_element_probability`, `fixed_unknown_weight`,
`unknown_combination_probability`, `concentration_scale`,
`allow_self_transition`, `global_seed`, `average_speed_mph`,
`target_total_miles`, per-layer duration parameters, and all seeds.

---

## 3. Random-number streams (reproducibility)

`ScenarioSimulator.__init__` creates one dedicated RNG per random source,
each seeded from `config.seeds`:

| seed key | RNG object | controls |
|---|---|---|
| `element_count` | `random.Random` | number of elements per layer (uniform 50–100) |
| `rarity_assignment` | `random.Random` | shuffling rarity categories across elements |
| `transition_matrix` | `numpy default_rng` | the Dirichlet draws of the transition vectors |
| `duration` | `random.Random` | every Gamma duration (initial + during simulation) |
| `initial_state` | `random.Random` | the initial element of each layer |
| `transition_sampling` | `random.Random` | next-element selection during simulation |

`global_seed` is separate and only feeds the SHA-256 unknown-combination
classifier (§7).

Because the streams are independent, changing one seed changes only its
own source: e.g. changing `duration` leaves element sets, rarity
assignments and transition vectors bit-identical
(`test_seed_streams_isolated`). Running twice with the same config
produces identical results down to every encounter
(`test_simulation_reproducible_with_same_seeds`).

---

## 4. Layer construction (`build_layer`)

Executed once per layer at initialization, consuming the streams above in
a fixed order (layer 0 → 5), which is what makes construction
deterministic.

**Step 1 — element count.** `n = rng_element_count.randint(50, 100)`
(bounds from config, inclusive), i.e. uniform over the integers 50…100.

**Step 2 — integer rarity counts** (`assign_rarity_counts`). The target
proportions (0.50 / 0.25 / 0.10 / 0.05 / 0.10) rarely give integers, so
the largest-remainder method is used: take `floor(n·p_r)` for each
category, then hand the remaining `n − Σ floors` elements to the
categories with the largest fractional parts. Guarantees: counts sum to
exactly `n`, and each count differs from the exact value `n·p_r` by less
than 1. *Worked example (the street layer of the delivered run, n = 76):*
exact values are 38 / 19 / 7.6 / 3.8 / 7.6 → floors 38 / 19 / 7 / 3 / 7
(sum 74, remainder 2) → the two largest fractions are very_rare (.8) and
rare (.6, tie with unknown broken by category order) → final counts
**38 / 19 / 8 / 4 / 7**.

**Step 3 — shuffle.** A list with each category repeated `count` times is
built and shuffled with `rng_rarity`, so *which* element index gets which
rarity is random, while the counts stay fixed.

**Step 4 — names.** Element `i` is named `f"{prefix}_{i:03d}"`, e.g.
`street_012` — the stable identifiers used in scenario strings and the
hash (§7).

**Step 5 — unknown weight** — see §5.

**Step 6 — weight vector and normalization.** Each element gets the weight
of its rarity (`common 1.0, medium 0.4, rare 0.1, very_rare 0.03,
unknown w_u`). The vector is normalized to sum to 1
(`initial_probs`) — this is also the distribution used to sample the
initial state (§8).

**Step 7 — fixed transition vector (Dirichlet).**

```
alpha            = concentration_scale · initial_probs      # default 100.0
transition_probs = np_rng_transition.dirichlet(alpha)       # ONE draw
```

The draw happens exactly once per layer, is stored permanently
(`Layer.transition_probs`) and is never resampled during simulation
(`test_transition_vectors_reproducible_and_permanent` verifies the array
is bit-identical before and after a run). The Dirichlet mean equals
`initial_probs`, so on average the vector follows the designed rarity
weights; `concentration_scale` controls how tightly a single draw sticks
to that design (higher = tighter, lower = more random). Cumulative sums
of both vectors are precomputed (`initial_cum`, `transition_cum`) so a
categorical sample is one uniform draw + one binary search
(`bisect_right`), O(log n).

**Step 8 — Gamma duration parameters** — see §6.

---

## 5. Unknown-element weight (`compute_unknown_weight`)

The point of the weighting: the goal is **not** that 0.4 % of elements
are unknown (10 % of them are), but that unknown elements are *selected*
≈ 0.4 % of the time during transitions. Two configurable modes:

**Mode `"fixed"`:** use `fixed_unknown_weight` (default 0.001) directly.
It must be smaller than the very_rare weight, else `ConfigError`.

**Mode `"calculated"` (default):** solve for the weight `w` that makes the
layer's total unknown probability mass equal the target `p`
(`target_unknown_element_probability`, default 0.004). With
`known_mass = n_c·w_c + n_m·w_m + n_r·w_r + n_vr·w_vr`, requiring

```
n_u · w / (known_mass + n_u · w) = p
```

and solving for `w` gives the formula from the assignment:

```
w = p · known_mass / (n_u · (1 − p))
```

*Worked example (street layer, counts 38/19/8/4/7):*
`known_mass = 38·1.0 + 19·0.4 + 8·0.1 + 4·0.03 = 46.52`, so
`w = 0.004 · 46.52 / (7 · 0.996) = 0.02669` — matching the delivered
`summary.md`, and indeed `7·0.02669 / (46.52 + 7·0.02669) = 0.4000 %`
exactly (the "designed unknown mass" column).

Guard rails: the calculated `w` must be strictly smaller than the
very_rare weight; otherwise a `ConfigError` tells the user to (1) increase
the proportion of unknown elements, (2) lower
`target_unknown_element_probability`, or (3) switch to
`unknown_weight_mode = "fixed"`. Calculated mode also requires at least
one unknown element per layer (division by `n_u`).

Because the *transition vector* is one Dirichlet draw around this design
(§4 step 7), the realized unknown mass of an individual layer scatters
around 0.4 % (variance set by `concentration_scale`); the design itself is
exact. See "Accuracy notes" in `README.md`.

---

## 6. Durations (`sample_gamma_duration`)

Every layer uses the same distribution family (Gamma) with per-layer mean
and variance from the config, converted by moment matching:

```
shape = mean² / variance        scale = variance / mean
```

(then E[X] = shape·scale = mean, Var[X] = shape·scale² = variance —
verified empirically in `test_gamma_parameterization_moments`).
A duration is drawn with `rng_duration.gammavariate(shape, scale)` each
time an element is entered, and clamped from below to
`min_duration_seconds` so durations are always positive
(`test_duration_positive_and_min_clamped`). All durations are seconds.

---

## 7. Unknown-combination classifier (`UnknownCombinationClassifier`)

Decides whether an *all-known* scenario tuple belongs to the fixed set of
"unknown combinations" — without ever enumerating or storing that set
(the scenario space, ~10¹¹ tuples, makes enumeration impossible).

For a tuple of element names the classifier performs the assignment's six
steps:

1. Stable string: `"street_012|temporal_004|ego_031|ru_008|environment_022|trigger_003"`.
2. Prefix with the seed: `"42|street_012|…|trigger_003"`.
3. SHA-256 of the UTF-8 bytes (`hashlib.sha256` — *not* Python's built-in
   `hash()`, which is salted per process and not stable across runs).
4. Digest → integer via `int.from_bytes(digest, "big")` (range 0…2²⁵⁶−1).
5. Normalize: `hash_value = integer / 2²⁵⁶` ∈ [0, 1).
6. Classify unknown iff `hash_value < unknown_combination_probability`
   (default 0.005).

Properties: **deterministic** (same tuple + same `global_seed` → same
answer, every run — `test_hash_classifier_deterministic`), **seed-dependent**
(changing `global_seed` selects a different fixed ≈0.5 % subset —
`test_hash_classifier_rate_and_seed_dependence`), **O(1) memory** (nothing
cached or stored — `test_hash_classifier_no_storage`), and ≈0.5 % of
random tuples classify unknown because SHA-256 output is uniform.
The set therefore *behaves* as if it existed permanently.

`ScenarioSimulator.classify_scenario(idx_tuple)` combines the two unknown
rules in order: if any of the six current elements has rarity `unknown` →
`(True, "unknown_element")`; else if the classifier flags the name tuple →
`(True, "unknown_combination")`; else known. Rule 2 is only ever evaluated
for all-known tuples, exactly as specified.

---

## 8. Initialization (`_new_state`)

1. For each layer, the initial element is sampled from the
   **rarity-weighted element probabilities** `initial_probs` (not the
   Dirichlet vector), using `rng_initial`.
2. One initial Gamma duration per selected element (`rng_duration`).
3. The initial scenario tuple is the combination of the six selections;
   `unknown_active` (a counter of layers currently on an unknown element)
   is initialized from it.
4. If `count_initial_scenario` is true (default), the initial tuple is
   classified once at t = 0 and counted as an encounter if unknown —
   entering the first tuple is entering a new scenario. Set it to false
   to count only subsequent changes.

The full mutable simulation state is a dict (`current`, `remaining`, `t`,
`miles`, `prev_tuple`, `unknown_active`, `encounters`, event/transition
counters, per-layer duration statistics, cumulative wall time). Keeping it
in one dict is what makes checkpoint/resume possible (§10).

---

## 9. Event-driven main loop (`run_resumable`)

The simulator never ticks second-by-second. Each iteration jumps directly
to the next instant at which at least one layer changes:

```
while miles < target:
    dt = min(remaining)                     # 1-2. next expiry
    t += dt                                 # 3.   advance time
    miles += mph * dt / 3600                # 4-5. advance mileage
    for k in layers:                        # 6.   age all layers
        remaining[k] -= dt
        if remaining[k] <= 1e-12: expired.append(k)   # 7.
    for k in expired:                       # 8.   update ALL expired layers
        next  = categorical(transition_cum[k])        #   fixed vector
        duration = gamma(shape[k], scale[k]) clamped  #   new duration
        update unknown_active if unknown-status changed
    new_tuple = tuple(current)              # 9.   ONE tuple per event
    if new_tuple != prev_tuple:             # 10.  entered a new scenario?
        if unknown_active > 0:              # 11.  rule 1 (unknown element)
            record Encounter("unknown_element", t, miles)
        elif sha256_check(new_tuple):       #      rule 2 (hash), §7
            record Encounter("unknown_combination", t, miles)
        prev_tuple = new_tuple              # 13.
```

Details worth knowing:

- **Floating-point expiry.** The layer that defined `dt` lands on exactly
  0.0 (IEEE `x − x = 0`); the `1e-12` tolerance only catches genuine
  simultaneous expiries. `dt` can never be negative because `dt` is the
  minimum of `remaining`.
- **Simultaneous expiries.** If several layers hit zero at the same event
  time, *all* of them are transitioned first, then exactly one tuple is
  built and exactly one unknown check performed — never one check per
  layer. At most one encounter can be counted per event step.
- **No double counting.** An encounter is recorded only when the new tuple
  *differs* from the previous one and is unknown. Staying inside the same
  unknown scenario for its whole duration counts once. A self-transition
  (allowed by default) reproduces the same tuple → no new scenario → no
  check. Entering a *different* unknown tuple (e.g. the ego layer changes
  while the environment layer still holds an unknown element) is a new
  scenario and counts again — that is what the spec requires and why
  encounters arrive in bursts (dispersion index ≫ 1, §11).
- **`unknown_active` counter.** Instead of scanning all six layers per
  event, the loop maintains a counter of how many layers currently sit on
  an unknown-rarity element, updated only when an expired layer's
  unknown-status flips. `unknown_active > 0` ⇔ rule 1 applies. The SHA-256
  check runs only for all-known tuples.
- **Self-transitions.** `allow_self_transition: false` uses rejection
  sampling (redraw until ≠ current), which is mathematically identical to
  renormalizing the vector with the current element removed
  (`test_no_self_transition_when_disabled`).
- **Mileage conversion.** `delta_miles = average_speed_mph · dt / 3600`
  with a constant configurable speed (default 50 mph). The stop condition
  is *miles* (2,000,000), not iterations or seconds; 2 M miles at 50 mph
  ≡ 144,000,000 simulated seconds, reached in ≈10 M events / ≈27 s of
  wall time.
- **Performance.** Per event: one `min` over 6 floats, ≤6 subtractions,
  ~1 categorical sample (binary search), ~1 Gamma draw, tuple compare, and
  (only on all-known changes) one SHA-256 of a ~60-byte string. Hot-loop
  variables are bound to locals; per-layer stats (transition counts,
  unknown selections, selections by rarity, duration sums) are updated
  incrementally.

`run()` is a thin wrapper: `run_resumable(state=None,
wall_limit_seconds=None)` → runs to completion and returns the
`SimulationResult`.

---

## 10. Checkpoint / resume

`run_resumable(state, wall_limit_seconds, …)` checks the wall clock every
4096 events; when the limit is exceeded it returns `(None, state)` instead
of a result. The runner then pickles `(simulator, state)` — the simulator
object carries all six RNG objects (their internal states pickle with
them), the layers, and the classifier; the state dict carries everything
mutable. Reloading and calling `run_resumable(state, …)` again continues
the exact random sequence, so a chunked run is **bit-identical** to an
uninterrupted one (`test_chunked_resume_bit_identical` proves equality of
event counts, times, and every encounter). CLI:

```bash
python run_simulation.py --checkpoint cp.pkl --max-wall-seconds 60   # chunk 1
python run_simulation.py --checkpoint cp.pkl --max-wall-seconds 60   # resumes
```

On completion the checkpoint file is deleted and results are written.

---

## 11. Output statistics

**Per encounter** (`Encounter` dataclass → `encounters.csv`): index,
mileage position, time position (s and h), reason
(`unknown_element` / `unknown_combination`), the full scenario string, and
both inter-arrival columns.

**Inter-arrivals** (`SimulationResult.inter_arrival_miles()` /
`inter_arrival_seconds()`): differences between consecutive encounter
positions; by convention the first entry is the distance/time from the
start of the simulation to the first encounter. Because speed is constant,
`gap_miles = mph · gap_seconds / 3600` holds for every pair
(`test_inter_arrival_times_and_distances_consistent`).

**Mileage windows** (`compute_window_stats`): the axis 0…total_miles is
cut into fixed windows of `mileage_window_miles` (default 10,000 →
200 windows for 2 M miles). Only *complete* windows are used, so the
partial overshoot window at the end cannot bias the statistics. Each
encounter increments its window `int(mileage // window_miles)`. Reported:
the count vector (`windows.csv`), the empirical mean count per window, the
empirical variance (sample variance, ddof = 1), and the
**dispersion index = variance / mean**. For a homogeneous Poisson process
the dispersion index is ≈1; the delivered run shows ≈12.4, i.e. strongly
clustered — the expected signature of encounter bursts while a slow layer
holds an unknown element (§9).

**Rate:** `encounters_per_million_miles() = N / (total_miles / 10⁶)`.

---

## 12. The runner (`run_simulation.py`)

CLI: `--config` (YAML path), `--outdir` (default `results/`),
`--no-plots`, `--checkpoint`, `--max-wall-seconds`. Flow: load config (or
resume a checkpoint) → print per-layer construction summary (element
counts, rarity counts, unknown weight, realized unknown mass) → run with
progress lines every 100,000 miles → write outputs:

| output | content |
|---|---|
| `encounters.csv` | one row per encounter: positions, reason, inter-arrivals, scenario |
| `windows.csv` | encounter count per mileage window |
| `summary.md` | totals, encounter stats, window/dispersion stats, per-layer table, verification vs configured targets |
| `stats.json` | the same, machine-readable |
| `plots/cumulative_encounters.png` | running encounter count vs mileage |
| `plots/inter_arrival_hist.png` | inter-arrival distance histogram (log y — burstiness visible) |
| `plots/unknown_rates_per_layer.png` | designed vs realized vs empirical unknown selection per layer + 0.4 % target line |
| `plots/rarity_selection_share.png` | selection share by rarity, expected vs empirical (log y) |
| `plots/window_counts.png` | per-window counts with mean/variance/dispersion annotation |

The `summary.md` verification section cross-checks the run against its
own configuration: overall unknown-element selection rate vs the 0.4 %
design target, hash-combination rate among all-known tuple changes vs
0.5 %, empirical vs configured mean durations, and exact time↔mileage
consistency.

---

## 13. Test suite (`test_simulator.py`, 29 tests)

Grouped by what they pin down: **hash classifier** — determinism across
calls, ≈0.5 % rate within 4σ on 20,000 random tuples, different
`global_seed` ⇒ different set, no hidden storage. **Rarity counts** —
largest-remainder counts sum to n and deviate < 1 for every n in 50…100.
**Unknown weight** — formula matches the spec algebraically, resulting
mass hits the target exactly, error message lists all three remedies,
fixed mode validated, calculated mode requires unknown elements.
**Validation** — bad proportions / mode / `base_weights['unknown']` /
malformed seeds all raise `ConfigError`. **Layers** — element counts in
range, unique names, unknown weight strictly smallest, transition vectors
valid probability vectors, designed unknown mass exactly 0.4 %, vectors
identical across rebuilds and untouched by running. **Seed isolation** —
each seed stream changes only its own source. **Durations** — Gamma
moments match mean/variance, min-clamp respected. **Classification** —
both unknown rules with correct reasons, deterministic re-classification.
**Counting** — same tuple never counted twice, different unknown tuple
counted once. **Simulation** — reaches target, time↔mileage consistent
(also per encounter), monotonic encounter ordering, window statistics on
hand-computable inputs, inter-arrival distance/time proportionality,
bit-identical reproducibility, bit-identical chunked resume.

Run with `pytest test_simulator.py -q`.
