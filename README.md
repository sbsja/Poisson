# Layered Scenario Model — Generated-Element Simulator (v6)

The simulator models 20,000 hours of autonomous-vehicle operation with six
generated layers. The only rarity classes are `common`, `rare`, and
`unknown`.

Semantic catalogues, fixed-element layers, rarity weights, and the analytical
unknown-weight solution have been removed.

## Direct class percentages

The user configures two percentage mappings in `config.yaml`. Both must
contain all three classes, use positive values, and sum to exactly 100:

```yaml
element_class_percentages:
  common: 70.0
  rare: 20.0
  unknown: 10.0

selection_class_percentages:
  common: 70.0
  rare: 20.0
  unknown: 10.0
```

`element_class_percentages` controls how many generated elements belong to
each class. Because counts must be integers, the simulator uses the
largest-remainder method.

`selection_class_percentages` controls the initial class masses and the target
class masses for transition-vector generation. With the default
`rescale_transition_class_masses: true`, the simulator randomly distributes
each mass among the elements inside its class and preserves the configured
class totals exactly. With the setting `false`, it keeps the raw seeded
Dirichlet vector, so realized transition class masses vary around the configured
targets. There are no intermediate class weights and no solved unknown
probability.

## Generated layers

| layer | generated element count |
|---|---:|
| street | 12 |
| temporal_modifications | uniform integer from 40–45 |
| ego_maneuver | uniform integer from 20–24 |
| ru_maneuver | uniform integer from 20–24 |
| environmental_conditions | 22 |
| triggering_conditions | uniform integer from 80–90 |

Generated IDs use stable prefixes within a run, such as `street_000`,
`ego_003`, and `trigger_042`. Counts and rarity placement are reproducible
from `seeds.element_count` and `seeds.rarity_assignment`.

## Element durations

Every element has its own Gamma duration distribution. Within each layer,
common elements have the longest configured mean-duration band, rare elements
the middle band, and unknown elements the shortest.

## Unknown scenarios

This is the simulator's only unknown-scenario mechanism. Standalone unknown
elements, hidden-triggering scenarios, hash/pattern classifiers, and
full-scenario probability classifiers are not part of the v6 runtime.

At initialization, the simulator selects configured numbers of exact C3, C4,
C5, and C6 rare-element combinations. Every combination contains rare elements
from distinct layers and includes one rare triggering-condition element.

A rule matches only when the complete active rare set exactly equals the
selected combination. All other active elements must be common.
Unknown-rarity elements disqualify a match.

## Stopping rule

The event loop stops exactly at `target_total_hours`, which defaults to
20,000 hours. Mileage is derived from elapsed time and
`average_speed_mph`; it is not the stopping criterion.

## Outputs

A completed run writes:

- `episodes.csv`
- `windows.csv`
- `summary.md`
- `stats.json`
- `plots/*.png`
- `duration_distributions/*.png`
- `duration_distributions/manifest.json`

`summary.md` and `stats.json` include:

- configured element-class percentages;
- configured selection-class percentages;
- exact integer counts and achieved element proportions per layer;
- the total element composition across all six layers;
- realized permanent transition mass by class for every layer.

`--no-plots` suppresses both plot folders.

## Run

```bash
pip install numpy pyyaml matplotlib pytest
python run_simulation.py --config config.yaml --outdir results
pytest test_simulator.py -q
```

For bit-identical chunked execution:

```bash
python run_simulation.py --checkpoint checkpoint.pkl --max-wall-seconds 60
```

## Main files

| file | purpose |
|---|---|
| `config.yaml` | generated-element configuration |
| `simulator.py` | simulation engine |
| `run_simulation.py` | command-line runner and result writers |
| `test_simulator.py` | automated tests |
| `DOCUMENTATION.md` | detailed implementation reference |
| `prompt_v6_changes.md` | v6 change report |
