# Duration Profile Element Spread Study

Tests sensitivity to heterogeneity between elements in the same rarity class.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 29.6 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| spread_0 | 0.0313 | 0.0001727 | 38.1698 | 1.8492 | 30.3333/0.6667/0.3333/0 |
| spread_0.025 | 0.0223 | 0.0001011 | 35.534 | 1.1252 | 22/0.3333/0/0 |
| spread_0.05 | 0.0287 | 0.0001723 | 39.7198 | 1.6133 | 28/0.6667/0/0 |
| spread_0.075 | 0.028 | 0.0001469 | 36.2399 | 1.0977 | 26.3333/1.6667/0/0 |
| spread_0.1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| spread_0.125 | 0.0257 | 0.0001365 | 33.6601 | 1.958 | 24/1.6667/0/0 |
| spread_0.15 | 0.0233 | 0.0001393 | 41.9288 | 0.9813 | 22.6667/0.6667/0/0 |
| spread_0.2 | 0.0237 | 0.0001258 | 42.1051 | 1.678 | 22.6667/1/0/0 |
| spread_0.25 | 0.0223 | 0.0001185 | 34.8136 | 1.1186 | 21.6667/0.6667/0/0 |
| spread_0.3 | 0.0233 | 0.0001448 | 46.2852 | 1.4683 | 21.3333/2/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `duration_profile_element_spread_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
