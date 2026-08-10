# Duration Profile Mean Multiplier Study

Tests how common, rare, and unknown sojourn means alter combination exposure.

## Design

- Levels: 30
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 88.4 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| common_1 | 0.0623 | 0.0003324 | 40.6199 | 1.3047 | 59/3.3333/0/0 |
| common_1.15 | 0.0453 | 0.0002534 | 40.1518 | 0.7749 | 41.6667/3.6667/0/0 |
| common_1.3 | 0.037 | 0.0001758 | 34.6729 | 1.5005 | 33.3333/3.6667/0/0 |
| common_1.5 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| common_1.75 | 0.0213 | 0.0001465 | 47.3593 | 2.1185 | 20/1.3333/0/0 |
| common_2 | 0.0177 | 0.0001223 | 53.3908 | 1.4213 | 17.3333/0.3333/0/0 |
| common_2.25 | 0.0103 | 6.471e-05 | 39.9823 | 1.8462 | 9.6667/0.6667/0/0 |
| common_2.5 | 0.006 | 5.581e-05 | 60.3243 | 0.8071 | 5.6667/0.3333/0/0 |
| common_2.75 | 0.004333 | 2.318e-05 | 32.3255 | 1.1667 | 4.3333/0/0/0 |
| common_3 | 0.004333 | 3.385e-05 | 43.1799 | 0.7321 | 4.3333/0/0/0 |
| rare_0.35 | 0.005333 | 1.718e-05 | 23.1427 | 0.4213 | 5.3333/0/0/0 |
| rare_0.45 | 0.011 | 4.796e-05 | 22.1058 | 1.5556 | 10.6667/0.3333/0/0 |
| rare_0.55 | 0.0223 | 7.967e-05 | 26.0019 | 1.0539 | 22/0.3333/0/0 |
| rare_0.65 | 0.0177 | 7.619e-05 | 27.8223 | 0.8184 | 17/0.3333/0.3333/0 |
| rare_0.75 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| rare_0.85 | 0.0297 | 0.0002373 | 57.048 | 0.7839 | 28.3333/1/0.3333/0 |
| rare_0.95 | 0.0387 | 0.0002556 | 48.9273 | 0.8802 | 38/0.6667/0/0 |
| rare_1.05 | 0.0397 | 0.0003649 | 73.9005 | 1.0169 | 38/1.6667/0/0 |
| rare_1.15 | 0.047 | 0.0003469 | 49.5859 | 0.6009 | 44/3/0/0 |
| rare_1.2 | 0.0393 | 0.0003473 | 60.2998 | 0.7593 | 37/2.3333/0/0 |
| unknown_0.05 | 0.0203 | 0.0001145 | 44.4475 | 0.7198 | 19.6667/0.6667/0/0 |
| unknown_0.1 | 0.0267 | 0.0001214 | 30.4255 | 1.779 | 25.6667/1/0/0 |
| unknown_0.15 | 0.0193 | 0.0001007 | 40.0751 | 1.2242 | 19/0.3333/0/0 |
| unknown_0.2 | 0.022 | 0.000108 | 40.0853 | 1.8843 | 22/0/0/0 |
| unknown_0.25 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| unknown_0.3 | 0.0257 | 0.0001295 | 38.62 | 1.8393 | 25/0.6667/0/0 |
| unknown_0.35 | 0.022 | 0.0001359 | 36.3068 | 1.8817 | 21.6667/0.3333/0/0 |
| unknown_0.4 | 0.0233 | 0.0001274 | 35.5052 | 0.9301 | 23/0.3333/0/0 |
| unknown_0.5 | 0.027 | 0.0001673 | 50.4571 | 0.9552 | 26.3333/0.6667/0/0 |
| unknown_0.6 | 0.019 | 0.0001101 | 36.1357 | 1.8944 | 18.3333/0.3333/0.3333/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `duration_profile_mean_multiplier_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `rarity_response_heatmap.png`
