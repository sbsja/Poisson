# Target Total Hours Study

Measures convergence and uncertainty as simulated observation time increases.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Simulation duration is supplied by each study level.
- Total wall time: 175.9 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| 50_hours | 0.04 | 0.000179 | 24.3648 | n/a | 2/0/0/0 |
| 100_hours | 0.0367 | 0.0002985 | 45.8059 | n/a | 3.6667/0/0/0 |
| 250_hours | 0.0253 | 0.0001657 | 43.9384 | 0 | 6/0.3333/0/0 |
| 500_hours | 0.0193 | 0.0001354 | 50.0071 | 1.1323 | 9/0.6667/0/0 |
| 1000_hours | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| 2000_hours | 0.0203 | 0.0001217 | 44.6616 | 1.0531 | 39/1.6667/0/0 |
| 5000_hours | 0.023 | 0.0001273 | 42.0817 | 1.0996 | 110/5/0/0 |
| 10000_hours | 0.0235 | 0.0001289 | 41.9274 | 1.2268 | 226.6667/8/0/0 |
| 15000_hours | 0.0235 | 0.000133 | 44.0067 | 1.2667 | 341/11/0/0 |
| 20000_hours | 0.0239 | 0.000136 | 43.1052 | 1.3683 | 463/15/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `target_total_hours_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
