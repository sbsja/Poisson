# Change Request v6 — Rare-Combination Unknown Scenarios

## Goal

Redefine the simulator around three rarity classes, element-dependent
durations, exact rare-element combinations as the only unknown-scenario route,
and a time-based simulation horizon.

## Changes made

### 1. Three rarity classes

The simulator accepts exactly `common`, `rare`, and `unknown`. Every layer uses
generated elements. Users directly configure element-class percentages and
selection-class percentages; both mappings contain all three classes and sum
to 100. Rarity weights and the calculated/fixed unknown-weight mechanism have
been removed.

### 2. One duration distribution per element

Every element stores its own Gamma mean, variance, shape, and scale. A layer's
`mean_duration` is the baseline and `duration_profiles` defines three
non-overlapping rarity bands. Catalog order places elements at stable, distinct
positions within each band without consuming an RNG stream.

| rarity | mean multiplier | within-class spread | coefficient of variation |
|---|---:|---:|---:|
| common | 1.50 | ±10% | 0.45 |
| rare | 0.75 | ±10% | 0.60 |
| unknown | 0.25 | ±10% | 0.80 |

Within every layer, all configured common means exceed all rare means and all
rare means exceed all unknown means. Per-element parameters are included in
`stats.json` layer metadata.

Completed runs with plotting enabled also create a separate
`duration_distributions/` folder. It contains one PDF/CDF comparison PNG per
layer, using the element nearest the median configured mean in each available
rarity class, plus a `manifest.json` recording the selected elements and their
Gamma parameters. `--no-plots` suppresses this folder together with the other
plot outputs.

### 3. Unknown scenarios are exact C3-C6 rare combinations

The old standalone element, hidden-triggering, hash, pattern, and
full-scenario-probability routes and their configuration fields have been
removed. Exact selected C3-C6 rare-element combinations are the only mechanism
that can open an unknown-scenario episode.

At initialization, the simulator selects combinations without replacement:

- C3: 40 combinations
- C4: 30 combinations
- C5: 20 combinations
- C6: 10 combinations

Each combination uses one rare element from each of distinct layers and must
include one rare element from `triggering_conditions`. Selection is uniform,
seeded by `seeds.combination_selection`, and implemented by sampling candidate ordinals
and unranking them. This avoids materializing potentially huge Cartesian
products.

A combination matches only when the current scenario's **complete rare set**
equals the selected set. A C3 is therefore not also active inside a C4. An
additional rare element or any unknown-rarity element disqualifies the match.
A self-transition that leaves the rare set unchanged continues the episode.

### 4. Time-based stopping

`target_total_hours` is the primary horizon and defaults to 20,000 hours. The
last event interval is clipped so the result ends at exactly 72,000,000
simulated seconds rather than overshooting to the next transition. Mileage is
derived as `average_speed_mph × elapsed_hours` for reporting.

A deprecated `target_total_miles` compatibility input is converted to time for
older studies, but the event loop itself is time-bounded.

## Configuration and validation

The `unknown_scenarios` section contains `enabled`, C3-C6
`combination_counts`, `require_triggering_condition`, and `exact_rare_set`.
The last two must be true. Invalid counts, insufficient eligible combinations,
obsolete rarity keys, overlapping duration bands, and mixed legacy routes fail
early.

## Verification

The v6 tests cover rarity validation, all profile variants, per-element
duration parameters and ordering, deterministic combination selection,
exact-set matching, triggering-condition inclusion, unknown-element
disqualification, removal of standalone routes, exact time stopping,
checkpoint/resume, output metadata, and conditional transitions.

Verification result: **39 tests passed**. Tests explicitly confirm that every
layer is generated and that each permanent class mass equals its configured
selection percentage.

## Assumption boundary

The duration multipliers and combination counts are explicit design defaults,
not empirical calibrations. They are centralized in `config.yaml` for tuning
without code changes.

## Generated-element composition update

Semantic-catalog and fixed-element construction have been removed. All six
layers sample or fix their generated element count through configured ranges,
allocate common/rare/unknown counts with the largest-remainder method, and
reproducibly shuffle those assignments.

`selection_class_percentages` assigns the exact permanent probability mass of
each class. One Dirichlet draw creates variation between elements inside each
class, after which each class is rescaled to its requested percentage. This
fully replaces the analytical unknown-weight solution.

Every run writes an `element_rarity_composition` object to `stats.json` and an
equivalent table to `summary.md`. Both contain exact counts and achieved
proportions per layer and for all six layers combined. Per-layer metadata also
reports the exact permanent transition mass of each class.
