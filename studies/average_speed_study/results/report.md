# Average Speed Study

Verifies that speed changes mileage-domain metrics but not time-domain dynamics.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 37.8 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| 5_mph | 0.02 | 0.0001333 | 47.6747 | n/a | 19.3333/0.6667/0/0 |
| 10_mph | 0.02 | 0.0001333 | 47.6747 | 0 | 19.3333/0.6667/0/0 |
| 20_mph | 0.02 | 0.0001333 | 47.6747 | 0.0667 | 19.3333/0.6667/0/0 |
| 30_mph | 0.02 | 0.0001333 | 47.6747 | 0.4345 | 19.3333/0.6667/0/0 |
| 40_mph | 0.02 | 0.0001333 | 47.6747 | 0.5795 | 19.3333/0.6667/0/0 |
| 50_mph | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| 60_mph | 0.02 | 0.0001333 | 47.6747 | 0.6437 | 19.3333/0.6667/0/0 |
| 75_mph | 0.02 | 0.0001333 | 47.6747 | 0.6978 | 19.3333/0.6667/0/0 |
| 100_mph | 0.02 | 0.0001333 | 47.6747 | 1.0205 | 19.3333/0.6667/0/0 |
| 150_mph | 0.02 | 0.0001333 | 47.6747 | 0.6916 | 19.3333/0.6667/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `average_speed_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
