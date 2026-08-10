# Selection Class Percentages Study

Tests how direct common/rare/unknown transition-selection mass changes exact rare-combination episodes.

## Design

- Levels: 20
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 78.5 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| rare_05pct | 0 | 0 | n/a | n/a | 0/0/0/0 |
| rare_10pct | 0.003667 | 3.145e-05 | 41.0456 | 0.5833 | 3.3333/0.3333/0/0 |
| rare_15pct | 0.009333 | 6.039e-05 | 46.3315 | 0.9438 | 9.3333/0/0/0 |
| rare_20pct | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| rare_25pct | 0.0417 | 0.000216 | 38.3354 | 1.7864 | 38/3.6667/0/0 |
| rare_30pct | 0.0907 | 0.0005019 | 39.1376 | 0.6249 | 86.6667/3.6667/0.3333/0 |
| rare_35pct | 0.1173 | 0.0006443 | 42.8838 | 1.0232 | 110/6.6667/0.6667/0 |
| rare_40pct | 0.1683 | 0.0009193 | 42.0118 | 1.3733 | 152.6667/15.3333/0.3333/0 |
| rare_45pct | 0.2387 | 0.001234 | 40.6275 | 1.5066 | 208.3333/27.3333/2.6667/0.3333 |
| rare_50pct | 0.301 | 0.001599 | 40.1876 | 1.8184 | 263/31/6.3333/0.6667 |
| unknown_1pct | 0.0173 | 0.0001114 | 47.3697 | 1.2229 | 17.3333/0/0/0 |
| unknown_3pct | 0.017 | 8.572e-05 | 33.042 | 1.3892 | 17/0/0/0 |
| unknown_5pct | 0.023 | 0.0001406 | 43.5896 | 1.9189 | 22/1/0/0 |
| unknown_7.5pct | 0.0223 | 0.0001155 | 40.0793 | 1.1888 | 21.3333/1/0/0 |
| unknown_10pct | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| unknown_12.5pct | 0.0297 | 0.0001537 | 38.785 | 0.5247 | 28/1/0.6667/0 |
| unknown_15pct | 0.0353 | 0.0002183 | 46.8808 | 0.9112 | 33.3333/2/0/0 |
| unknown_20pct | 0.0267 | 0.000136 | 37.2404 | 0.8185 | 25.6667/0.6667/0.3333/0 |
| unknown_25pct | 0.0387 | 0.0001955 | 36.7333 | 1.3622 | 38/0.6667/0/0 |
| unknown_30pct | 0.0337 | 0.0001574 | 35.2632 | 2.379 | 31/2.6667/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `selection_class_percentages_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `selection_percentage_sweeps.png`
