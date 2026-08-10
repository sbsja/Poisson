# Combination Size Study

Isolates the strong rarity effect of requiring 3, 4, 5, or 6 rare layers.

## Design

- Levels: 12
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 46.4 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| none | 0 | 0 | n/a | n/a | 0/0/0/0 |
| c3_only_40 | 0.0193 | 0.0001312 | 48.3347 | 0.6469 | 19.3333/0/0/0 |
| c4_only_40 | 0.0006667 | 3.797e-06 | 26.294 | 0.75 | 0/0.6667/0/0 |
| c5_only_40 | 0 | 0 | n/a | n/a | 0/0/0/0 |
| c6_only_40 | 0 | 0 | n/a | n/a | 0/0/0/0 |
| c3_c4 | 0.0273 | 0.0001743 | 45.1214 | 0.886 | 26/1.3333/0/0 |
| c4_c5 | 0.001333 | 4.764e-06 | 23.399 | 1.5 | 0/1/0.3333/0 |
| c5_c6 | 0 | 0 | n/a | n/a | 0/0/0/0 |
| equal_25 | 0.0133 | 9.109e-05 | 46.5934 | 0.6731 | 12.6667/0.3333/0.3333/0 |
| front_loaded | 0.0423 | 0.0002355 | 41.3899 | 1.2873 | 41.3333/1/0/0 |
| baseline | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| reverse | 0.004667 | 3.783e-05 | 53.7714 | 1.0833 | 4.3333/0.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `combination_size_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `configured_vs_observed_combination_sizes.png`
