# Combination Counts Study

Measures how total selected-rule coverage affects episode frequency.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 38.0 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| scale_0 | 0 | 0 | n/a | n/a | 0/0/0/0 |
| scale_0.1 | 0.001 | 1.208e-05 | 65.5696 | 0.5 | 1/0/0/0 |
| scale_0.25 | 0.004333 | 3.526e-05 | 54.4969 | 1 | 4.3333/0/0/0 |
| scale_0.5 | 0.009 | 6.341e-05 | 52.4507 | 0.8611 | 8.6667/0.3333/0/0 |
| scale_0.75 | 0.0147 | 9.725e-05 | 46.7909 | 0.7513 | 14.3333/0.3333/0/0 |
| scale_1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| scale_1.5 | 0.036 | 0.0002119 | 42.403 | 1.2915 | 34.3333/1.6667/0/0 |
| scale_2 | 0.0477 | 0.000253 | 40.4811 | 1.2645 | 45.3333/2.3333/0/0 |
| scale_3 | 0.0737 | 0.0004155 | 41.5245 | 1.484 | 72.6667/1/0/0 |
| scale_5 | 0.1253 | 0.0006572 | 38.4573 | 2.1865 | 122/3.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `combination_counts_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `configured_vs_observed_combination_sizes.png`
- `numeric_response_curves.png`
