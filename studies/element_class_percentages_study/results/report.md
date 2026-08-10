# Element Class Percentages Study

Tests dilution and catalogue-composition effects at fixed class selection mass.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 28.5 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| rare_elements_6pct | 0.8027 | 0.004861 | 47.6007 | 2.5634 | 700/94.6667/7.6667/0.3333 |
| rare_elements_8pct | 0.277 | 0.001745 | 48.8347 | 1.3218 | 253.3333/23/0.6667/0 |
| rare_elements_10pct | 0.24 | 0.00131 | 42.2563 | 0.5043 | 224/14.6667/1.3333/0 |
| rare_elements_15pct | 0.0503 | 0.0003523 | 45.908 | 0.6087 | 48/2.3333/0/0 |
| rare_elements_20pct | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| rare_elements_25pct | 0.007 | 4.656e-05 | 54.4634 | 1.9312 | 7/0/0/0 |
| rare_elements_30pct | 0.006333 | 4.307e-05 | 48.2747 | 1.0556 | 6.3333/0/0/0 |
| rare_elements_35pct | 0.003667 | 1.267e-05 | 14.5145 | 1.0741 | 3.3333/0.3333/0/0 |
| rare_elements_40pct | 0.003333 | 1.428e-05 | 21.4074 | 0.9722 | 3.3333/0/0/0 |
| rare_elements_50pct | 0.002 | 1.081e-05 | 28.566 | 1.5833 | 2/0/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `element_class_percentages_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
