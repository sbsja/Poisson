# Layer Element Count Study

Measures per-element probability dilution as each layer catalogue changes size.

## Design

- Levels: 60
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 190.0 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| street_n6 | 0.0303 | 0.0001648 | 35.5381 | 0.8532 | 29/1.3333/0/0 |
| street_n8 | 0.02 | 0.0001016 | 41.4151 | 0.8352 | 19/0.6667/0.3333/0 |
| street_n9 | 0.0283 | 0.0001686 | 49.9811 | 2.042 | 28/0.3333/0/0 |
| street_n10 | 0.0197 | 0.0001098 | 37.1031 | 0.477 | 18.6667/1/0/0 |
| street_n12 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| street_n14 | 0.0263 | 0.0001717 | 48.543 | 0.8728 | 26/0.3333/0/0 |
| street_n15 | 0.024 | 0.000157 | 44.7976 | 0.5766 | 23.3333/0.6667/0/0 |
| street_n16 | 0.0287 | 0.0001845 | 45.0788 | 1.5289 | 27.3333/1.3333/0/0 |
| street_n18 | 0.02 | 0.0001197 | 39.3775 | 0.4671 | 20/0/0/0 |
| street_n20 | 0.0183 | 0.0001042 | 34.5208 | 0.6085 | 18.3333/0/0/0 |
| temporal_modifications_n21 | 0.0343 | 0.0001957 | 43.7193 | 0.8896 | 32.3333/1.3333/0.6667/0 |
| temporal_modifications_n27 | 0.0283 | 0.0001134 | 32.2778 | 0.9974 | 27.6667/0.6667/0/0 |
| temporal_modifications_n32 | 0.0257 | 0.0001586 | 40.6613 | 2.0812 | 25.3333/0.3333/0/0 |
| temporal_modifications_n37 | 0.0297 | 0.0001368 | 33.1327 | 1.8718 | 28/1.6667/0/0 |
| temporal_modifications_n42 | 0.02 | 0.000164 | 69.2304 | 1.0516 | 19.3333/0.6667/0/0 |
| temporal_modifications_n48 | 0.0163 | 0.0001178 | 51.562 | 1.0995 | 16/0.3333/0/0 |
| temporal_modifications_n53 | 0.0257 | 0.0001738 | 46.9454 | 0.8328 | 24/1.6667/0/0 |
| temporal_modifications_n58 | 0.0127 | 7.901e-05 | 37.4785 | 0.7454 | 12.3333/0.3333/0/0 |
| temporal_modifications_n64 | 0.0187 | 9.684e-05 | 32.8565 | 0.9921 | 18.3333/0.3333/0/0 |
| temporal_modifications_n69 | 0.016 | 8.193e-05 | 42.8213 | 1.5787 | 15.3333/0.6667/0/0 |
| ego_maneuver_n11 | 0.0417 | 0.00024 | 40.3932 | 0.9424 | 40/1.6667/0/0 |
| ego_maneuver_n14 | 0.0253 | 0.0001451 | 42.1155 | 0.7677 | 24/1.3333/0/0 |
| ego_maneuver_n16 | 0.037 | 0.0002103 | 39.6981 | 1.4631 | 36.6667/0.3333/0/0 |
| ego_maneuver_n19 | 0.0227 | 0.0001208 | 39.1185 | 0.7891 | 22.3333/0.3333/0/0 |
| ego_maneuver_n22 | 0.024 | 0.0001218 | 41.0102 | 1.7866 | 23.6667/0.3333/0/0 |
| ego_maneuver_n25 | 0.0223 | 0.0001366 | 46.2919 | 1.5606 | 21.6667/0.6667/0/0 |
| ego_maneuver_n28 | 0.024 | 0.0001491 | 50.9137 | 0.6674 | 22.6667/0.6667/0.6667/0 |
| ego_maneuver_n30 | 0.0173 | 8.855e-05 | 33.7928 | 0.8285 | 17/0.3333/0/0 |
| ego_maneuver_n33 | 0.019 | 0.0001222 | 44.8179 | 1.048 | 19/0/0/0 |
| ego_maneuver_n36 | 0.0197 | 0.0001239 | 44.1552 | 1.5283 | 19/0.6667/0/0 |
| ru_maneuver_n11 | 0.0323 | 0.0001771 | 37.9401 | 1.1945 | 31.6667/0.6667/0/0 |
| ru_maneuver_n14 | 0.031 | 0.0001626 | 38.5671 | 1.0479 | 29/2/0/0 |
| ru_maneuver_n16 | 0.0277 | 0.0001539 | 36.6424 | 0.3887 | 26.6667/1/0/0 |
| ru_maneuver_n19 | 0.026 | 0.0001332 | 35.4312 | 1.6511 | 25.3333/0.6667/0/0 |
| ru_maneuver_n22 | 0.02 | 9.722e-05 | 35.3943 | 0.7583 | 18.3333/1.6667/0/0 |
| ru_maneuver_n25 | 0.0273 | 0.0001517 | 39.2305 | 0.582 | 27/0.3333/0/0 |
| ru_maneuver_n28 | 0.0217 | 0.0001227 | 38.9994 | 0.9494 | 21.3333/0.3333/0/0 |
| ru_maneuver_n30 | 0.022 | 0.0001182 | 36.98 | 0.9692 | 22/0/0/0 |
| ru_maneuver_n33 | 0.0203 | 0.0001388 | 44.0183 | 1.1323 | 20/0.3333/0/0 |
| ru_maneuver_n36 | 0.0203 | 0.0001186 | 47.0706 | 1.5746 | 18/2/0.3333/0 |
| environmental_conditions_n11 | 0.036 | 0.00023 | 48.1788 | 0.954 | 35/1/0/0 |
| environmental_conditions_n14 | 0.0237 | 0.0001247 | 34.9126 | 0.5714 | 23/0.6667/0/0 |
| environmental_conditions_n16 | 0.026 | 0.0001189 | 39.9967 | 1.2649 | 25/1/0/0 |
| environmental_conditions_n19 | 0.0257 | 0.0001508 | 36.8752 | 2.0415 | 25/0.6667/0/0 |
| environmental_conditions_n22 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| environmental_conditions_n25 | 0.0193 | 9.266e-05 | 34.2273 | 2.1306 | 18.6667/0.6667/0/0 |
| environmental_conditions_n28 | 0.0247 | 0.0001478 | 38.9604 | 0.6343 | 23.6667/1/0/0 |
| environmental_conditions_n30 | 0.022 | 0.0001381 | 44.8954 | 0.5376 | 21.6667/0.3333/0/0 |
| environmental_conditions_n33 | 0.0207 | 0.0001159 | 38.8865 | 1.997 | 20/0.6667/0/0 |
| environmental_conditions_n36 | 0.0177 | 0.0001009 | 39.9842 | 1.613 | 17/0.6667/0/0 |
| triggering_conditions_n42 | 0.0483 | 0.0002985 | 46.8638 | 0.6076 | 47.6667/0.6667/0/0 |
| triggering_conditions_n53 | 0.0383 | 0.000235 | 46.6503 | 0.9733 | 37/1.3333/0/0 |
| triggering_conditions_n64 | 0.0413 | 0.0002097 | 35.5638 | 0.9101 | 40.3333/1/0/0 |
| triggering_conditions_n74 | 0.0323 | 0.0001534 | 35.866 | 0.9646 | 30.3333/2/0/0 |
| triggering_conditions_n85 | 0.0217 | 0.0001126 | 42.7942 | 0.4615 | 21/0.6667/0/0 |
| triggering_conditions_n96 | 0.02 | 0.0001163 | 38.5908 | 1.5173 | 18.3333/1.6667/0/0 |
| triggering_conditions_n106 | 0.019 | 8.527e-05 | 35.3071 | 1.4885 | 19/0/0/0 |
| triggering_conditions_n117 | 0.0173 | 0.0001103 | 38.1757 | 1.3358 | 16.6667/0.6667/0/0 |
| triggering_conditions_n128 | 0.0233 | 0.0001293 | 35.1116 | 1.2728 | 22.3333/1/0/0 |
| triggering_conditions_n138 | 0.0173 | 8.854e-05 | 38.877 | 0.9878 | 17/0.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `layer_element_count_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `layer_response_heatmap.png`
