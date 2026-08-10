# Duration Profile Coefficient Of Variation Study

Tests duration-tail and clustering sensitivity at fixed element means.

## Design

- Levels: 30
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 91.7 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| common_0.1 | 0.0267 | 0.0001353 | 38.179 | 1.0768 | 26.3333/0.3333/0/0 |
| common_0.2 | 0.025 | 0.0001532 | 46.5343 | 1.2873 | 24.3333/0.6667/0/0 |
| common_0.35 | 0.027 | 0.0001445 | 37.7335 | 0.9709 | 26.6667/0.3333/0/0 |
| common_0.5 | 0.0243 | 0.0001752 | 48.2822 | 0.892 | 23.6667/0.6667/0/0 |
| common_0.65 | 0.027 | 0.0001777 | 44.4693 | 0.6208 | 26.3333/0.6667/0/0 |
| common_0.8 | 0.0243 | 0.000165 | 48.6862 | 0.669 | 24/0.3333/0/0 |
| common_1 | 0.0283 | 0.0001537 | 34.948 | 1.9873 | 27.6667/0.6667/0/0 |
| common_1.25 | 0.023 | 0.0001192 | 39.6654 | 1.254 | 22/1/0/0 |
| common_1.5 | 0.0187 | 0.000102 | 36.1715 | 0.9907 | 18.6667/0/0/0 |
| common_2 | 0.0307 | 0.0001845 | 51.1933 | 1.1429 | 29.3333/1.3333/0/0 |
| rare_0.1 | 0.0297 | 0.0001808 | 42.3098 | 1.5512 | 28.3333/1.3333/0/0 |
| rare_0.2 | 0.0247 | 0.0001518 | 49.291 | 1.6089 | 23.6667/1/0/0 |
| rare_0.35 | 0.0263 | 0.0001631 | 42.6638 | 1.3543 | 25/1.3333/0/0 |
| rare_0.5 | 0.0263 | 0.0001461 | 35.1086 | 1.0084 | 26/0.3333/0/0 |
| rare_0.65 | 0.0247 | 0.0001543 | 42.484 | 1.1994 | 23.3333/1.3333/0/0 |
| rare_0.8 | 0.0257 | 0.0001324 | 35.7252 | 0.6453 | 24/1.3333/0.3333/0 |
| rare_1 | 0.0207 | 9.803e-05 | 34.574 | 0.803 | 19.3333/1/0.3333/0 |
| rare_1.25 | 0.0257 | 0.0001173 | 34.602 | 0.6667 | 24.6667/1/0/0 |
| rare_1.5 | 0.0227 | 0.000133 | 48.2356 | 2.7307 | 22.6667/0/0/0 |
| rare_2 | 0.0283 | 0.0001564 | 59.235 | 0.5437 | 28/0.3333/0/0 |
| unknown_0.1 | 0.0227 | 0.0001375 | 37.9583 | 0.8204 | 21.6667/1/0/0 |
| unknown_0.2 | 0.0287 | 0.0001544 | 35.4525 | 0.6266 | 27.6667/1/0/0 |
| unknown_0.35 | 0.0297 | 0.0001718 | 41.1959 | 0.764 | 29.3333/0.3333/0/0 |
| unknown_0.5 | 0.0227 | 0.0001566 | 47.0941 | 0.9736 | 22/0.6667/0/0 |
| unknown_0.65 | 0.0223 | 0.0001264 | 46.1334 | 1.597 | 21/1.3333/0/0 |
| unknown_0.8 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| unknown_1 | 0.026 | 0.0001254 | 38.053 | 1.2104 | 25/1/0/0 |
| unknown_1.25 | 0.027 | 0.00016 | 45.6905 | 0.7244 | 27/0/0/0 |
| unknown_1.5 | 0.0203 | 9.309e-05 | 37.5791 | 1.4077 | 20/0.3333/0/0 |
| unknown_2 | 0.0267 | 0.0001558 | 40.1648 | 1.1414 | 26.3333/0.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `duration_profile_coefficient_of_variation_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `rarity_response_heatmap.png`
