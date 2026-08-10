# Mileage Window Study

Measures how reporting-window scale changes count dispersion, not state history.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 2000 simulated hours.
- Total wall time: 77.1 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| 100_miles | 0.0203 | 0.0001217 | 44.6616 | 1.0686 | 39/1.6667/0/0 |
| 250_miles | 0.0203 | 0.0001217 | 44.6616 | 1.188 | 39/1.6667/0/0 |
| 500_miles | 0.0203 | 0.0001217 | 44.6616 | 1.1565 | 39/1.6667/0/0 |
| 1000_miles | 0.0203 | 0.0001217 | 44.6616 | 1.1913 | 39/1.6667/0/0 |
| 2500_miles | 0.0203 | 0.0001217 | 44.6616 | 1.6055 | 39/1.6667/0/0 |
| 5000_miles | 0.0203 | 0.0001217 | 44.6616 | 1.4104 | 39/1.6667/0/0 |
| 10000_miles | 0.0203 | 0.0001217 | 44.6616 | 1.0531 | 39/1.6667/0/0 |
| 25000_miles | 0.0203 | 0.0001217 | 44.6616 | 1.1618 | 39/1.6667/0/0 |
| 50000_miles | 0.0203 | 0.0001217 | 44.6616 | 0.4209 | 39/1.6667/0/0 |
| 100000_miles | 0.0203 | 0.0001217 | 44.6616 | 0 | 39/1.6667/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `mileage_window_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
