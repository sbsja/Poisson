# Layered Scenario Model — Event-Driven AV Simulator

Simulates an autonomous vehicle driving 2,000,000 miles through a 6-layer
scenario model and counts encounters with *unknown scenarios*.

## Files

| File | Purpose |
|---|---|
| `config.yaml` | All parameters (documented inline) |
| `simulator.py` | Core model: layers, weights, Dirichlet vectors, durations, hash classifier, event-driven engine, window statistics |
| `run_simulation.py` | CLI runner: writes `encounters.csv`, `windows.csv`, `summary.md`, `stats.json`, plots |
| `test_simulator.py` | 29 pytest unit tests |
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

## Outputs

The simulator reports: total simulated mileage; total simulated time in
seconds; total number of unknown scenario encounters; the mileage and time
position of each encounter plus inter-arrival distances and times
(`encounters.csv`, stats in `summary.md`/`stats.json`); unknown-encounter
count per fixed mileage window (`windows.csv`, window size
`mileage_window_miles`, default 10,000 mi) with empirical mean count,
empirical variance, and dispersion index = variance/mean; and the estimated
unknown encounter rate per million miles. Window statistics use only
complete windows so a partial final window cannot bias them. A dispersion
index > 1 (observed ≈ 12) means encounters are clustered, which is expected:
while a slow layer holds an unknown element, every fast-layer change creates
a new unknown tuple.

## Reproducibility

Every random source has its own configurable seed (config section `seeds`):
`element_count` (elements per layer), `rarity_assignment` (category
shuffle), `transition_matrix` (Dirichlet sampling), `duration` (Gamma
sampling, initial + simulation), `initial_state` (initial elements), and
`transition_sampling` (next-element selection during simulation). The
hash-based unknown-combination method uses `global_seed`. Running twice
with the same config and seeds produces identical results (unit-tested,
including across checkpoint/resume). Seed-stream isolation is also tested:
e.g. changing only the `duration` seed leaves element sets, rarities, and
transition vectors untouched.

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

- **One shared transition vector per layer** (chosen ov