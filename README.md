# Layered Scenario Model — Event-Driven AV Simulator

Simulates an autonomous vehicle driving 2,000,000 miles through a 6-layer
scenario model and counts encounters with *unknown scenarios*.

## Files

| File | Purpose |
|---|---|
| `config.yaml` | All parameters (documented inline) |
| `simulator.py` | Core model: layers, weights, Dirichlet vectors, durations, hash classifier, event-driven engine |
| `run_simulation.py` | CLI runner: writes `encounters.csv`, `summary.md`, `stats.json`, plots |
| `test_simulator.py` | 24 pytest unit tests |
| `results/` | Output of the default 2M-mile run |

## How to run

```bash
pip install numpy pyyaml matplotlib pytest
python run_simulation.py --config config.yaml --outdir results
pytest test_simulator.py -q            # unit tests
```

Long runs can be paused/resumed with bit-identical results:

```bash
python run_simulation.py --checkpoint cp.pkl --max-wall-seconds 60
python run_simulation.py --checkpoint cp.pkl --max-wall-seconds 60   # resumes
```

## Model

**Layers (fixed order):** street, temporal_modifications, ego_maneuver,
ru_maneuver, environmental_conditions, triggering_conditions (unexpected AV
triggers). Layers are fully independent — no conditional probabilities
between layers; each has its own transition probability vector.

**Elements.** Per layer, the element count is sampled uniformly from
[50, 100]. Rarity categories (common/medium/rare/very_rare/unknown) are
assigned with the configured proportions using largest-remainder integer
counts, then randomly shuffled across elements. Element IDs follow the spec
format, e.g. `street_012`.

**Weights.** Base weights per rarity come from the config (common 1.0,
medium 0.4, rare 0.1, very_rare 0.03). The unknown weight is always the
smallest and has two configurable modes:

- `calculated` (default): per layer, `w = p·known_mass / (n_unknown·(1−p))`
  with `p = target_unknown_element_probability` (default 0.004), which makes
  the layer's unknown probability mass *exactly* p. If `w ≥ very_rare`
  weight, a `ConfigError` tells the user to raise the unknown proportion,
  lower the target, or switch to fixed mode.
- `fixed`: uses `fixed_unknown_weight` (default 0.001); must also be
  `< very_rare` weight.

**Transitions.** At initialization only, each layer's normalized weight
vector is turned into one permanent transition probability vector by a
single Dirichlet draw with `alpha = concentration_scale · normalized_weights`
(default 100.0). It is never resampled during simulation.
Self-transitions are allowed by default (`allow_self_transition`); when
disabled, sampling rejects the current element (equivalent to renormalizing
without it).

**Durations.** Entering an element samples a Gamma duration with per-layer
mean/variance (`shape = mean²/var`, `scale = var/mean`), clamped to
`min_duration_seconds`. All durations are in seconds.

**Unknown scenarios.** A scenario tuple (the ordered 6-element combination)
is unknown if (1) any element has rarity `unknown`, or (2) all elements are
known but the tuple is in the hash-defined unknown-combination set:
`sha256("<global_seed>|street_..|temporal_..|...")` normalized by 2²⁵⁶ and
compared to `unknown_combination_probability` (default 0.005). This is
deterministic across runs (SHA-256, not Python's `hash()`), seeded, O(1)
per query, and never stores or enumerates combinations.

**Event-driven loop.** Each step jumps by the smallest remaining duration,
advances time and mileage (`delta_miles = mph·dt/3600`, default 50 mph),
subtracts dt from all layers, transitions *all* expired layers, then builds
one new scenario tuple and performs exactly one unknown check. An encounter
is counted only when the simulator enters a *different* tuple that is
unknown — staying inside the same unknown scenario counts once, and
simultaneous multi-layer expiries produce one check, so there is no double
counting. The stop condition is 2,000,000 *miles* (not iterations/seconds).

## Design decisions & assumptions

- **One shared transition vector per layer** (chosen over a full per-element
  matrix): next-element probabilities depend on target rarity, not on the
  current element.
- **Initial scenario at t=0 is checked and counted if unknown**
  (`count_initial_scenario`, default true), since entering the first tuple
  is entering a new scenario. Set to `false` to only count changes.
- **Two RNG streams, one seed:** `random.Random(simulation_seed)` drives the
  hot loop; `numpy default_rng(simulation_seed)` drives the Dirichlet draws.
  Same `simulation_seed` ⇒ bit-identical runs (unit-tested).
- **Per-layer duration defaults** are plausibility choices (ego maneuver
  ~30 s … environment ~30 min) and freely configurable.
- **Encounter bursts are expected:** while a slow layer sits on an unknown
  element, every change in a fast layer creates a *new* unknown tuple and
  counts again (per spec). Hence the low median (~0.3 mi) vs mean (~13 mi)
  inter-arrival distance.

## Accuracy notes (worth knowing)

- With `concentration_scale = 100`, each layer's *realized* unknown mass is
  a Beta(≈0.4, ≈99.6) draw around the 0.4% design target — individual
  layers can land at 0.01% or 0.6% (see
  `results/plots/unknown_rates_per_layer.png`). The design mass is exact;
  the scatter comes from the spec's Dirichlet step. Raise
  `concentration_scale` (e.g. 10,000) if realized rates must sit near 0.4%.
- The empirical unknown-combination rate in the 2M-mile run was 0.5022%
  vs the 0.5% target; empirical durations matched configured means, and
  mileage/time are exactly consistent (40,000 h at 50 mph).
