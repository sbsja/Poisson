# Parameter-sensitivity study (v6)

This report aggregates the specifically named current-v6 studies. It replaces the legacy ranking based on removed unknown mechanisms.

## Seed-only noise control

| metric | mean | seed SD | runs |
|---|---:|---:|---:|
| episodes_per_hour | 0.02355 | 0.00653311 | 20 |
| unknown_time_fraction | 0.000139004 | 5.43419e-05 | 20 |

## Ranking

SNR is the range across a study's swept level means divided by the seed-only standard deviation. Structural and categorical studies are ranked by range but should not be interpreted as linear trends.

| rank | study | levels | rate SNR | rate range % | occupancy SNR | occupancy range % |
|---:|---|---:|---:|---:|---:|---:|
| 1 | element_class_percentages_study | 10 | 122.56 | 3399.9% | 89.25 | 3489.1% |
| 2 | selection_class_percentages_study | 20 | 46.07 | 1278.1% | 29.42 | 1150.3% |
| 3 | combination_counts_study | 10 | 19.18 | 532.2% | 12.09 | 472.8% |
| 4 | duration_profile_mean_multiplier_study | 30 | 8.88 | 246.3% | 6.40 | 250.2% |
| 5 | combination_size_study | 12 | 6.48 | 179.8% | 4.33 | 169.4% |
| 6 | layer_mean_duration_study | 60 | 6.22 | 172.7% | 1.56 | 60.9% |
| 7 | layer_element_count_study | 60 | 5.46 | 151.5% | 4.04 | 157.9% |
| 8 | target_total_hours_study | 10 | 3.16 | 87.8% | 3.25 | 127.2% |
| 9 | unknown_scenarios_enabled_study | 2 | 3.06 | 84.9% | 2.45 | 95.9% |
| 10 | conditional_transition_study | 12 | 2.45 | 67.9% | 1.24 | 48.4% |
| 11 | concentration_scale_study | 10 | 1.84 | 51.0% | 1.56 | 61.0% |
| 12 | duration_profile_coefficient_of_variation_study | 30 | 1.84 | 51.0% | 1.68 | 65.8% |
| 13 | duration_profile_element_spread_study | 10 | 1.73 | 48.1% | 1.32 | 51.5% |
| 14 | allow_self_transition_study | 2 | 1.53 | 42.5% | 0.18 | 7.1% |
| 15 | minimum_duration_study | 10 | 1.53 | 42.5% | 0.49 | 19.0% |
| 16 | duration_distribution_study | 10 | 1.48 | 41.0% | 1.03 | 40.4% |
| 17 | rescale_transition_class_masses_study | 2 | 0.71 | 19.8% | 0.70 | 27.3% |
| 18 | average_speed_study | 10 | 0.00 | 0.0% | 0.00 | 0.0% |
| 19 | layer_variance_duration_study | 60 | 0.00 | 0.0% | 0.00 | 0.0% |
| 20 | mileage_window_study | 10 | 0.00 | 0.0% | 0.00 | 0.0% |

## Limitations

The component studies are screening runs. Wide grids intentionally include extreme settings, so the ranking describes the tested ranges, not an intrinsic unit-free importance. Confirm the leading factors with longer paired runs and interaction studies.

## Charts

- `sensitivity_tornado.png`: ranked rate and occupancy SNR.
- `sensitivity_metric_heatmap.png`: cross-metric comparison.
- `effect_noise_scatter.png`: factors affecting rate, occupancy, or both.
