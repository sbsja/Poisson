# Minimum Duration Study

Tests clamp-induced duration bias, transition suppression, and episode persistence.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 38.1 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| 0.001_seconds | 0.0237 | 0.0001293 | 34.108 | 1.7224 | 23.3333/0.3333/0/0 |
| 0.01_seconds | 0.0247 | 0.0001216 | 31.3888 | 1.7843 | 24/0.6667/0/0 |
| 0.1_seconds | 0.022 | 0.0001187 | 33.4963 | 1.8564 | 21.6667/0.3333/0/0 |
| 0.5_seconds | 0.025 | 0.0001387 | 45.5036 | 1.5256 | 24.3333/0.6667/0/0 |
| 1_seconds | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| 2_seconds | 0.0233 | 0.0001405 | 39.5457 | 1.8617 | 22.6667/0.6667/0/0 |
| 5_seconds | 0.0243 | 0.0001238 | 32.3487 | 1.1148 | 23.3333/1/0/0 |
| 10_seconds | 0.0273 | 0.0001417 | 37.1523 | 1.4062 | 26.3333/1/0/0 |
| 20_seconds | 0.0173 | 0.0001153 | 48.5011 | 1.8263 | 16.6667/0.6667/0/0 |
| 30_seconds | 0.022 | 0.000135 | 44.8267 | 1.2909 | 20.3333/1.6667/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `minimum_duration_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `numeric_response_curves.png`
