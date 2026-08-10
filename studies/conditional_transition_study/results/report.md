# Conditional Transition Study

Tests concentration of ego rare behavior when the street layer is rare.

## Design

- Levels: 12
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 450.4 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| independent | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| conditional_x0 | 0.027 | 0.0001707 | 45.5997 | 0.4501 | 26.6667/0.3333/0/0 |
| conditional_x0.1 | 0.0277 | 0.0001759 | 48.5779 | 0.399 | 26.6667/1/0/0 |
| conditional_x0.25 | 0.02 | 0.0001096 | 35.2581 | 0.7358 | 19.6667/0.3333/0/0 |
| conditional_x0.5 | 0.023 | 0.0001322 | 38.1319 | 1.8904 | 21.3333/1.6667/0/0 |
| conditional_x0.75 | 0.0273 | 0.00016 | 46.6932 | 0.8584 | 27.3333/0/0/0 |
| conditional_x1 | 0.0217 | 0.0001401 | 45.387 | 1.2136 | 19.3333/2/0.3333/0 |
| conditional_x1.5 | 0.0253 | 0.0001297 | 40.83 | 0.643 | 24.3333/1/0/0 |
| conditional_x2 | 0.026 | 0.0001319 | 33.7932 | 2.9211 | 25.6667/0.3333/0/0 |
| conditional_x4 | 0.0263 | 0.0001391 | 38.5566 | 1.0753 | 23.6667/2.6667/0/0 |
| conditional_x10 | 0.034 | 0.0001472 | 32.4378 | 1.6489 | 32.3333/1.6667/0/0 |
| conditional_x100 | 0.036 | 0.0001769 | 33.0879 | 0.9497 | 34.3333/1.3333/0.3333/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `conditional_transition_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
