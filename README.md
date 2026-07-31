# Layered Scenario Model — Event-Driven AV Simulator (v5)

Simulates an autonomous vehicle driving 2,000,000 miles through a 6-layer
scenario model and measures **unknown episodes**: how often the vehicle
enters an unknown scenario and **how long each one lasts**. The current
configuration tracks visible element unknowns, a hidden triggering-condition
category, and rare all-known full-scenario tuples.

## Files

| File | Purpose |
|---|---|
| `config.yaml` | Shared default and complete v5-S semantic configuration |
| `config_semantic_catalog_v5s.yaml` | Named Semantic Catalog Simulator profile |
| `config_semantic_catalog_v2.yaml` | High-quality fixed semantic catalog v2.0 profile |
| `config_generated_elements_v5g.yaml` | Named Generated Element Simulator profile with anonymous IDs |
| `SIMULATOR_PROFILES.md` | Profile differences, element amounts, and run commands |
| `SEMANTIC_CATALOG_V2.md` | v2 fixed counts, primary sources, and quality requirements |
| `simulator.py` | Core model + event-driven engine + episode tracking |
| `run_simulation.py` | CLI runner: `episodes.csv`, `windows.csv`, `summary.md`, `stats.json`, plots |
| `test_simulator.py` | pytest unit and integration tests |
| `SEMANTIC_CATALOGS.md` | v5 catalog definitions, assumptions, and versioning policy |
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

Two deliberately distinct profiles are available:

```bash
# v5-S: stable semantic IDs such as lane_follow and sensor_occlusion
python run_simulation.py --config config_semantic_catalog_v5s.yaml --outdir results_semantic_v5s

# v5-G: anonymous IDs such as ego_000 and trigger_000
python run_simulation.py --config config_generated_elements_v5g.yaml --outdir results_generated_v5g

# catalog v2.0: larger fixed catalogs with source traceability
python run_simulation.py --config config_semantic_catalog_v2.yaml --outdir results_semantic_v2
```

See `SIMULATOR_PROFILES.md` for the complete profile comparison. Profile names
are recorded in the console, `summary.md`, and `stats.json`.

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

## The six layers (v5-S semantic configuration)

| layer | elements | unknowns? | source |
|---|---|---|---|
| street | **12 fixed real elements** with exact transition probabilities (no Dirichlet) | no | user route-composition data |
| temporal_modifications | **16 semantic elements**, catalog v1.0 | yes | temporary traffic-control concepts |
| ego_maneuver | **13 semantic elements**, catalog v1.0 | yes | stable maneuver taxonomy |
| ru_maneuver | **14 semantic elements**, catalog v1.0 | yes | surrounding-road-user interaction taxonomy |
| environmental_conditions | **13 semantic elements**, catalog v1.0 | **no** | lighting, weather, visibility, surface, and wind concepts |
| triggering_conditions | **11 semantic elements**, catalog v1.0 | yes | perception, map, signage, geometry, and interference triggers |

The street layer's 12 route-composition probabilities are used **exactly**
as its permanent transition vector and initial-state distribution. Every
non-street layer now has stable IDs, labels, descriptions, and explicit
rarities from semantic catalog version 1.0. Rarity-based weights retain the
calculated unknown weight (exact 0.4% designed unknown mass), followed by one
permanent transition-vector draw from
Dirichlet(`concentration_scale` · normalized weights). These weights are
engineering assumptions, not measurements from real driving data. Legacy
generated element-count ranges remain supported for older configurations.

`concentration_scale = 20000` comes from `concentration_study.md`: the
smallest tested value for which ≥95% of Dirichlet draws land within ±25%
of the 0.4% unknown-rate target (the old default 100 gave ~10% and
per-layer rates anywhere between 0.003% and 0.5%).

## Independent and conditional transitions

`transition_model.mode` selects how the next element is sampled:

- `independent` is the backward-compatible default. Each layer samples from
  its permanent vector without considering the other layers.
- `conditional` multiplies a target layer's base probabilities by every
  matching rule, normalizes the result, and samples with the existing RNG.
  Conditions across layers are AND; element/rarity selectors within a layer
  are OR. Dependencies must form an acyclic graph.

Complete independent configuration:

```yaml
transition_model:
  mode: independent
  conditional:
    apply_to_initial_state: true
    rules: []                 # dormant rules are also allowed here
```

Complete conditional example:

```yaml
transition_model:
  mode: conditional
  conditional:
    apply_to_initial_state: true
    rules:
      - id: merge_affects_ego
        target_layer: ego_maneuver
        when:
          street:
            elements: [forced_merge_proceeding, forced_merge_merging]
        multipliers:
          elements: {merge: 4.0}
          rarities: {rare: 1.5, common: 0.7}

full_scenario_unknowns:
  enabled: false
```

If multiple layers expire together, parent layers are sampled before their
dependants; unrelated ties use the fixed six-layer order. Conditional rules
are deterministic and consume no random numbers themselves. The v5 defaults
reference stable semantic IDs such as `merge`; only legacy generated-layer
configurations use seed-dependent names such as `ego_003`.

The current `full_scenario_unknowns` classifier multiplies independent
stationary probabilities. Conditional mode therefore rejects configurations
that enable it until dependency-aware rarity calibration is implemented.
Conditional weighting can also move empirical unknown rates away from the
0.4% baseline construction target; the summary and JSON outputs report this.

## Outputs

Totals (mileage, time, events); every episode with layer, stable element ID,
label, description, catalog version,
start/end mileage and time, duration in seconds and miles, truncated flag
(`episodes.csv`); episode-duration statistics; inter-arrival distances and
times between episode starts; episode-start counts per fixed mileage
window with empirical mean, variance, and dispersion index =
variance/mean (`windows.csv`); episodes per million miles; total time in
an unknown scenario as the union of episode intervals; and six plots.
Conditional runs also report dependency order, rule matches, influenced
transitions, matched/unmatched selections, and empirical unknown occupancy.

## Reproducibility

One configurable seed per random source (`seeds:` in the config):
element_count, rarity_assignment, transition_matrix, duration,
initial_state, transition_sampling, pattern_rules; `global_seed` drives
the hash classifier. The same config produces identical results, including
across checkpoint/resume (unit-tested) in both transition modes. Conditional
rules consume no randomness themselves. The street layer consumes no
construction randomness: its vector is exact regardless of seeds.
Semantic catalogs also consume neither `element_count` nor
`rarity_assignment`; those streams remain solely for legacy generated layers.

## v5: Semantic element catalogs (current)

All five non-street layers use fixed, ordered catalog version `1.0`. Catalog
IDs and rarity assignments do not change with construction seeds, so
conditional rules and downstream analysis remain meaningful across runs.
Configuration validation enforces exactly one construction form per layer and
checks catalog structure, stable snake-case IDs, uniqueness, rarity values,
unknown consistency, and unknown-weight feasibility. See
`SEMANTIC_CATALOGS.md` and `prompt_v5_changes.md`.

## Headline results of the delivered 2M-mile run (seeds as in config)

The checked-in `results/` directory was generated before combinations were
disabled and is retained as a historical baseline. Regenerate the run after
this configuration change before interpreting its totals as results of the
current multi-route model.


## v4: Full-scenario rarity unknowns (retained in v5)

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
configuration's latest results live in `results_current/`.**
