# Layer Mean Duration Study

Measures transition-rate and persistence sensitivity to every layer time scale.

## Design

- Levels: 60
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 197.5 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| street_x0.25 | 0.027 | 0.0001289 | 34.3906 | 1.0714 | 26/1/0/0 |
| street_x0.4 | 0.025 | 0.0001322 | 40.0264 | 1.0946 | 25/0/0/0 |
| street_x0.55 | 0.0253 | 0.0001459 | 39.9262 | 1.7873 | 24.3333/1/0/0 |
| street_x0.7 | 0.0257 | 0.0001547 | 46.149 | 1.2952 | 25/0.6667/0/0 |
| street_x0.85 | 0.0213 | 0.0001309 | 47.6113 | 1.5115 | 21.3333/0/0/0 |
| street_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| street_x1.25 | 0.022 | 0.0001332 | 48.8893 | 0.7641 | 22/0/0/0 |
| street_x1.5 | 0.0277 | 0.0001636 | 42.5124 | 0.87 | 27.3333/0.3333/0/0 |
| street_x2 | 0.0223 | 0.0001182 | 35.2111 | 1.2078 | 22.3333/0/0/0 |
| street_x3 | 0.021 | 0.000147 | 42.5131 | 0.7357 | 20.3333/0.6667/0/0 |
| temporal_modifications_x0.25 | 0.0257 | 0.0001713 | 48.8979 | 0.5253 | 24.6667/1/0/0 |
| temporal_modifications_x0.4 | 0.024 | 0.0001277 | 36.306 | 0.7178 | 24/0/0/0 |
| temporal_modifications_x0.55 | 0.023 | 0.0001317 | 42.9696 | 2.007 | 22.6667/0.3333/0/0 |
| temporal_modifications_x0.7 | 0.0227 | 0.0001322 | 46.8748 | 0.7606 | 22.3333/0.3333/0/0 |
| temporal_modifications_x0.85 | 0.023 | 0.0001362 | 47.9851 | 1.4697 | 23/0/0/0 |
| temporal_modifications_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| temporal_modifications_x1.25 | 0.027 | 0.0001429 | 39.7243 | 0.603 | 26.6667/0.3333/0/0 |
| temporal_modifications_x1.5 | 0.028 | 0.0001515 | 38.9726 | 2.2066 | 27.6667/0.3333/0/0 |
| temporal_modifications_x2 | 0.0173 | 9.478e-05 | 45.4966 | 1.8694 | 17/0.3333/0/0 |
| temporal_modifications_x3 | 0.031 | 0.0001628 | 34.562 | 1.1555 | 31/0/0/0 |
| ego_maneuver_x0.25 | 0.056 | 0.0001646 | 22.323 | 2.9457 | 54/2/0/0 |
| ego_maneuver_x0.4 | 0.04 | 0.0001436 | 29.3356 | 1.9193 | 39.6667/0.3333/0/0 |
| ego_maneuver_x0.55 | 0.0377 | 0.000158 | 28.558 | 1.9621 | 37.3333/0.3333/0/0 |
| ego_maneuver_x0.7 | 0.0297 | 0.0001628 | 52.7722 | 2.3411 | 29.3333/0.3333/0/0 |
| ego_maneuver_x0.85 | 0.028 | 0.0001696 | 48.0979 | 1.6907 | 28/0/0/0 |
| ego_maneuver_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| ego_maneuver_x1.25 | 0.0237 | 0.0001549 | 46.2692 | 1.2052 | 23.3333/0.3333/0/0 |
| ego_maneuver_x1.5 | 0.0233 | 0.000146 | 47.7882 | 1.6226 | 23.3333/0/0/0 |
| ego_maneuver_x2 | 0.0227 | 0.0001594 | 48.5251 | 1.4471 | 22/0.6667/0/0 |
| ego_maneuver_x3 | 0.0153 | 0.0001091 | 50.8061 | 2.2837 | 15.3333/0/0/0 |
| ru_maneuver_x0.25 | 0.0447 | 0.0001568 | 28.794 | 0.5666 | 43.6667/1/0/0 |
| ru_maneuver_x0.4 | 0.033 | 0.0001423 | 29.4427 | 1.0619 | 31.6667/1.3333/0/0 |
| ru_maneuver_x0.55 | 0.0283 | 0.0001364 | 33.338 | 1.0332 | 27.3333/1/0/0 |
| ru_maneuver_x0.7 | 0.024 | 0.0001224 | 37.217 | 1.8765 | 22.6667/1.3333/0/0 |
| ru_maneuver_x0.85 | 0.0263 | 0.0001764 | 40.2298 | 1.2537 | 25/1.3333/0/0 |
| ru_maneuver_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| ru_maneuver_x1.25 | 0.023 | 0.000137 | 39.6108 | 1.1736 | 21.6667/1.3333/0/0 |
| ru_maneuver_x1.5 | 0.02 | 0.0001259 | 41.7792 | 0.7083 | 19.3333/0.6667/0/0 |
| ru_maneuver_x2 | 0.021 | 0.0001279 | 41.0396 | 1.8201 | 20/1/0/0 |
| ru_maneuver_x3 | 0.0227 | 0.0001637 | 52.65 | 2.0326 | 22.3333/0.3333/0/0 |
| environmental_conditions_x0.25 | 0.028 | 0.0001775 | 53.7867 | 0.9444 | 27/1/0/0 |
| environmental_conditions_x0.4 | 0.0197 | 0.0001183 | 46.1386 | 1.7077 | 18.6667/0.6667/0.3333/0 |
| environmental_conditions_x0.55 | 0.026 | 0.0001794 | 64.9286 | 0.7781 | 25.3333/0.6667/0/0 |
| environmental_conditions_x0.7 | 0.0243 | 0.0001442 | 40.58 | 0.9846 | 23.6667/0.6667/0/0 |
| environmental_conditions_x0.85 | 0.0243 | 0.0001414 | 44.873 | 1.8956 | 24/0.3333/0/0 |
| environmental_conditions_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| environmental_conditions_x1.25 | 0.0263 | 0.0001703 | 47.1046 | 0.7742 | 25.6667/0.6667/0/0 |
| environmental_conditions_x1.5 | 0.028 | 0.0001417 | 32.9211 | 1.3362 | 27/1/0/0 |
| environmental_conditions_x2 | 0.023 | 0.0001256 | 38.1842 | 1.0391 | 22.6667/0.3333/0/0 |
| environmental_conditions_x3 | 0.022 | 0.0001307 | 45.1583 | 1.7188 | 20/2/0/0 |
| triggering_conditions_x0.25 | 0.0433 | 0.0001578 | 23.6633 | 1.6792 | 41.6667/1.6667/0/0 |
| triggering_conditions_x0.4 | 0.036 | 0.0001632 | 33.2844 | 2.5809 | 34/2/0/0 |
| triggering_conditions_x0.55 | 0.0297 | 0.0001393 | 35.1503 | 0.6461 | 28.6667/1/0/0 |
| triggering_conditions_x0.7 | 0.026 | 0.0001319 | 37.2788 | 0.6162 | 25.3333/0.6667/0/0 |
| triggering_conditions_x0.85 | 0.0287 | 0.0001678 | 45.0262 | 1.4279 | 27.3333/1.3333/0/0 |
| triggering_conditions_x1 | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| triggering_conditions_x1.25 | 0.0187 | 0.0001064 | 38.3776 | 0.7563 | 17.6667/1/0/0 |
| triggering_conditions_x1.5 | 0.023 | 0.0001483 | 44.4012 | 2.0566 | 22.3333/0.6667/0/0 |
| triggering_conditions_x2 | 0.021 | 0.0001571 | 52.4628 | 0.9878 | 20.6667/0.3333/0/0 |
| triggering_conditions_x3 | 0.021 | 0.0001446 | 50.0967 | 1.0639 | 21/0/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `layer_mean_duration_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
- `layer_response_heatmap.png`
