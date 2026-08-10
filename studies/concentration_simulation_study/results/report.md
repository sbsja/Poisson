# Concentration Scale Study

Measures within-class probability concentration and seed sensitivity under the v6 direct-class-mass model.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 28.9 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| c_100 | 0.024 | 0.0001288 | 38.3385 | 2.5639 | 24/0/0/0 |
| c_300 | 0.032 | 0.0002005 | 49.9379 | 0.928 | 31.3333/0.6667/0/0 |
| c_1000 | 0.0247 | 0.0001299 | 36.7647 | 1.0278 | 24/0.6667/0/0 |
| c_3000 | 0.03 | 0.0001994 | 51.6214 | 0.5038 | 28/2/0/0 |
| c_10000 | 0.023 | 0.0001257 | 38.3747 | 1.9056 | 22.6667/0.3333/0/0 |
| c_20000 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| c_50000 | 0.0267 | 0.0001673 | 42.8274 | 1.0313 | 26/0.6667/0/0 |
| c_100000 | 0.0287 | 0.0001393 | 34.3034 | 0.7207 | 28.6667/0/0/0 |
| c_300000 | 0.027 | 0.0001657 | 42.679 | 1.4975 | 25.3333/1.6667/0/0 |
| c_1000000 | 0.0223 | 0.0001157 | 34.1077 | 0.5242 | 22/0.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `concentration_scale_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
