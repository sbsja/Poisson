# Layered Scenario Model — Event-Driven AV Simulator (v3)

Simulates an autonomous vehicle driving 2,000,000 miles through a 6-layer
scenario model and measures **unknown episodes**: how often the vehicle
enters an unknown scenario and **how long each one lasts**. The delivered
configuration tracks unknown **elements** only.

## Files

| File | Purpose |
|---|---|
| `config.yaml` | All parameters (documented inline) |
| `simulator.py` | Core model + event-driven engine + episode tracking |
| `run_simulation.py` | CLI runner: `episodes.csv`, `windows.csv`, `summary.md`, `stats.json`, plots |
| `test_simulator.py` | 38 pytest unit tests |
| `results/` | Output of the default 2M-mile run |
| `research_element_counts.md` | Literature research behind the per-layer element counts |
| `concentration_study.py/.md/.png` | Study behind `concentration_scale = 20000` |
| `prompt_v2_changes.md` | The change request this version implements |
| `DOCUMENTATION.md` | Detailed how-it-works reference |

## How to run

```bash
pip install numpy pyyaml matplotlib pytest
python run_simulation.py --config config.yaml --outdir results
pytest test_simulator.py -q
# optional chunked execution (bit-identical to a single run):
python run_simulation.py --checkpoint cp.pkl --max-wall-seconds 60
```

## Unknown-episode semantics (v2 — replaces per-tuple counting)

An unknown **episode** is a contiguous occupancy of one unknown element by
one layer: it starts when a layer transitions from a known to an unknown
element (or at t=0 if it starts there), and ends when **that layer** moves
to a known element. A direct hop to a *different* unknown element closes
the episode and opens a new one; a self-transition onto the same unknown
element continues it. Episodes are per layer and may overlap — a second
layer entering an unknown element is a second, separate episode with its
own duration — and changes in other layers never start or end an episode.
Episodes still open at the end of the run are closed and flagged
`truncated`. One unknown period = one count, however many other layers
change meanwhile.

**Unknown combinations:** Pattern and hash combinations are disabled in the
delivered configuration. No rules are loaded or generated, and the hash
classifier is not instantiated or evaluated. The union unknown time therefore
contains only overlapping element-level unknown episodes.

## The six layers (v2 configuration)

| layer | elements | unknowns? | source |
|---|---|---|---|
| street | **12 fixed real elements** with exact transition probabilities (no Dirichlet) | no | user route-composition data |
| temporal_modifications | sampled [30, 46] | yes | max = 46 MUTCD Part-6 typical applications; min flagged as modeling choice |
| ego_maneuver | sampled [7, 12] | yes | 7 = IGP2 maneuver library; research max 14 clipped to 12 for feasibility (see `research_element_counts.md`) |
| ru_maneuver | sampled [7, 12] | yes | same taxonomy family; 14-maneuver study; same clip |
| environmental_conditions | sampled [15, 21] | **no** (known proportions renormalized) | 15 = CARLA weather presets; 21 = BSI PAS 1883 environment leaves |
| triggering_conditions | sampled [50, 100] | yes | unchanged by design — TODO: investigate varying this layer's element count later |

The street layer's 12 route-composition probabilities are used **exactly**
as its permanent transition vector and initial-state distribution. All
other sampled layers get rarity categories (largest-remainder + shuffle),
rarity-based weights with a calculated unknown weight (exact 0.4% designed
unknown mass; must stay below the very_rare weight — every n in a
configured range is feasibility-checked at validation), and one permanent
transition vector drawn once from
Dirichlet(`concentration_scale` · normalized weights).

`concentration_scale = 20000` comes from `concentration_study.md`: the
smallest tested value for which ≥95% of Dirichlet draws land within ±25%
of the 0.4% unknown-rate target (the old default 100 gave ~10% and
per-layer rates anywhere between 0.003% and 0.5%).

## Outputs

Totals (mileage, time, events); every episode with layer, element,
start/end mileage and time, duration in seconds and miles, truncated flag
(`episodes.csv`); episode-duration statistics; inter-arrival distances and
times between episode starts; episode-start counts per fixed mileage
window with empirical mean, variance, and dispersion index =
variance/mean (`windows.csv`); episodes per million miles; total time in
an unknown scenario as the union of episode intervals; and six plots.

## Reproducibility

One configurable seed per random source (`seeds:` in the config):
element_count, rarity_assignment, transition_matrix, duration,
initial_state, transition_sampling, pattern_rules; `global_seed` drives
the hash classifier. The same config produces identical results, including
across checkpoint/resume (unit-tested). The street layer consumes no
randomness: its vector is exact regardless of seeds.

## Headline results of the delivered 2M-mile run (seeds as in config)

The checked-in `results/` directory was generated before combinations were
disabled and is retained as a historical baseline. Regenerate the run after
this configuration change before interpreting its totals as results of the
current element-only model.


## v4: Full-scenario rarity unknowns (current)

Pattern and hash combinations are **disabled**. In addition to the
unchanged element-level episodes, a scenario-level mechanism classifies
the COMPLETE six-layer tuple S by its stationary probability
P(S) = product of the six realized transition-vector probabilities. For
the full-scenario route, S must contain known elements in all six layers
and P(S) must be <= a threshold calibrated once at
initialization (deterministic Monte Carlo from the stationary product
distribution, dedicated `calibration_seed`) so that the total stationary
MASS of rare tuples matches `target_stationary_mass` (0.4%). Episode
semantics: open on entering a rare tuple, close when the exact tuple
changes to a known one, close+reopen on rare A -> rare B, unaffected by
self-transitions. Configuration: `full_scenario_unknowns` in config.yaml.

**Delivered run (`results_full_scenario/`)** predates the three-route change
below; regenerate it before comparing results.

The simulator now treats unknown scenarios through three non-overlapping
routes: a normal unknown element in a visible unknown-bearing layer; a
dedicated `hidden_triggering_unknown` episode whenever the hidden triggering
conditions layer is unknown; or a rare full six-layer combination made only
of known elements. The full-scenario route is therefore never used for a
tuple already covered by either element route.

**NOTE: the historical `results/` directory predates this configuration
and is NOT valid for it — regenerate before comparing. The current
configuration's results live in `results_full_scenario/`.**
