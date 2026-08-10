# Seed Variability Study

Quantifies natural run-to-run variability with no behavioral parameter change.

## Design

- Levels: 20
- Paired independent seed sets per level: 1
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 25.2 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| seed_set_01 | 0.02 | 0.0001093 | 35.2239 | 0.875 | 19/1/0/0 |
| seed_set_02 | 0.019 | 0.0001253 | 45.6491 | 0.5789 | 19/0/0/0 |
| seed_set_03 | 0.021 | 0.0001654 | 62.151 | 0.1667 | 20/1/0/0 |
| seed_set_04 | 0.026 | 0.0001583 | 46.6235 | 3.7885 | 25/1/0/0 |
| seed_set_05 | 0.026 | 0.000182 | 46.9365 | 0.7879 | 26/0/0/0 |
| seed_set_06 | 0.026 | 0.0001398 | 38.8616 | 2.9697 | 25/1/0/0 |
| seed_set_07 | 0.017 | 0.0001086 | 46.1617 | 1.2647 | 16/1/0/0 |
| seed_set_08 | 0.016 | 5.589e-05 | 31.8974 | 2.4062 | 16/0/0/0 |
| seed_set_09 | 0.032 | 0.0001754 | 54.1999 | 0.3594 | 30/2/0/0 |
| seed_set_10 | 0.014 | 8.674e-05 | 39.6391 | 1.5 | 14/0/0/0 |
| seed_set_11 | 0.028 | 0.0001541 | 44.3658 | 1.125 | 28/0/0/0 |
| seed_set_12 | 0.016 | 6.72e-05 | 29.5852 | 0.6667 | 13/3/0/0 |
| seed_set_13 | 0.04 | 0.0003156 | 53.0264 | 0.4375 | 40/0/0/0 |
| seed_set_14 | 0.024 | 0.0001427 | 38.8062 | 2.6458 | 24/0/0/0 |
| seed_set_15 | 0.031 | 0.0001198 | 31.0275 | 0.7701 | 28/3/0/0 |
| seed_set_16 | 0.017 | 0.0001043 | 50.04 | 1.5128 | 17/0/0/0 |
| seed_set_17 | 0.029 | 0.000148 | 40.1627 | 2.2759 | 26/3/0/0 |
| seed_set_18 | 0.02 | 0.0001088 | 38.1321 | 0.6667 | 20/0/0/0 |
| seed_set_19 | 0.025 | 0.0001718 | 54.8767 | 0.3 | 25/0/0/0 |
| seed_set_20 | 0.024 | 0.0001412 | 51.4532 | 0.5625 | 23/1/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `seed_variability_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `seed_caterpillar.png`
