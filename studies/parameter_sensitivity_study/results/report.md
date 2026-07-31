# Parameter-sensitivity study (one-at-a-time)

## What this answers

Each simulator parameter was varied on its own from the delivered `config.yaml` baseline while every other setting was held fixed. Every variant, including the untouched baseline, was run for 5 independent seed sets at 2,000,000 miles each. The baseline's spread across those seeds is the **seed-only noise band** (the negative control): the natural run-to-run variation of the model when nothing is changed.

A parameter's influence is reported as a **signal-to-noise ratio** = (range of a metric across the parameter's swept levels) / (baseline seed standard deviation of that metric). A ratio near or below 1 means sweeping the parameter moved the output no more than reshuffling the random seeds would---i.e. no detectable effect. A large ratio means a real effect. **No fixed cut-off is applied here**; the ranking is laid out so a threshold can be chosen from the numbers below.

## Seed-only noise band (baseline, negative control)

| metric | baseline mean | seed SD | seed CV |
|---|---:|---:|---:|
| episodes_per_million_miles | 3.717e+04 | 1125 | 3.03% |
| unknown_time_fraction | 0.02035 | 0.0002081 | 1.02% |
| total_unknown_episodes | 7.433e+04 | 2250 | 3.03% |
| total_events | 9.999e+06 | 1479 | 0.01% |
| duration_s_mean | 39.64 | 0.8495 | 2.14% |
| duration_s_median | 21.21 | 0.3391 | 1.60% |
| duration_s_p90 | 70.84 | 1.792 | 2.53% |
| duration_mi_mean | 0.5506 | 0.0118 | 2.14% |
| inter_arrival_mi_mean | 26.93 | 0.8241 | 3.06% |
| inter_arrival_s_mean | 1939 | 59.33 | 3.06% |
| dispersion_index | 4.87 | 0.3965 | 8.14% |
| episodes_element | 3.325e+04 | 2168 | 6.52% |
| episodes_hidden_triggering | 4931 | 477.5 | 9.68% |
| episodes_full_scenario | 3.615e+04 | 434.8 | 1.20% |

## Sensitivity ranking

Factors sorted by their maximum signal-to-noise across the two primary outputs (episode rate and unknown-time fraction). `SNR` columns are effect-range / baseline-seed-SD; `%` columns are effect-range as a percent of the baseline mean; `trend` is the direction versus the swept level (numeric factors only).

| factor | rate SNR | rate % | rate trend | unknown-frac SNR | unknown-frac % | unknown-frac trend | infeasible levels? |
|---|---:|---:|---|---:|---:|---|:--:|
| fixed_unknown_weight | 16.8 | 50.9% | increasing | 76.8 | 78.5% | increasing |  |
| target_unknown_element_probability | 12.7 | 38.5% | increasing | 58.6 | 59.9% | increasing | yes |
| average_speed_mph | 49.3 | 149.2% | decreasing | 0.6 | 0.7% | decreasing |  |
| full_scenario_target_mass | 24.0 | 72.7% | increasing | 29.0 | 29.7% | increasing |  |
| mean_duration.ego_maneuver | 23.9 | 72.4% | decreasing | 0.8 | 0.8% | increasing |  |
| allow_self_transition | 15.2 | 46.1% | n/a | 19.6 | 20.1% | n/a |  |
| full_scenario_enabled | 16.1 | 48.6% | n/a | 19.3 | 19.7% | n/a |  |
| transition_mode_conditional | 15.6 | 47.2% | categorical | 18.2 | 18.6% | categorical |  |
| mean_duration.ru_maneuver | 15.8 | 47.7% | decreasing | 0.8 | 0.8% | increasing |  |
| concentration_scale | 3.4 | 10.2% | non-monotonic | 9.2 | 9.4% | non-monotonic |  |
| mean_duration.triggering_conditions | 6.4 | 19.3% | decreasing | 0.2 | 0.2% | decreasing |  |
| min_duration_seconds | 4.5 | 13.6% | non-monotonic | 1.0 | 1.0% | non-monotonic |  |
| element_count.temporal_modifications | 0.8 | 2.5% | decreasing | 4.3 | 4.4% | decreasing |  |
| element_count.triggering_conditions | 0.2 | 0.5% | non-monotonic | 1.7 | 1.8% | non-monotonic |  |
| variance_duration.temporal_modifications | 0.1 | 0.4% | increasing | 1.5 | 1.5% | increasing |  |
| mean_duration.street | 1.2 | 3.8% | decreasing | 1.3 | 1.3% | increasing |  |
| element_count.environmental_conditions | 0.1 | 0.2% | increasing | 1.3 | 1.3% | decreasing |  |
| mean_duration.temporal_modifications | 1.3 | 3.9% | decreasing | 0.8 | 0.8% | decreasing |  |
| element_count.ego_maneuver | 0.2 | 0.7% | increasing | 1.1 | 1.1% | decreasing |  |
| element_count.ru_maneuver | 0.6 | 1.7% | increasing | 1.1 | 1.1% | increasing |  |
| mean_duration.environmental_conditions | 0.2 | 0.5% | decreasing | 1.0 | 1.0% | increasing |  |
| variance_duration.ru_maneuver | 0.3 | 1.0% | increasing | 0.9 | 0.9% | increasing |  |
| variance_duration.street | 0.2 | 0.7% | increasing | 0.8 | 0.9% | increasing |  |
| unknown_proportion | 0.3 | 1.0% | n/a | 0.7 | 0.8% | n/a | yes |
| base_weights_shape | 0.0 | 0.1% | categorical | 0.6 | 0.6% | categorical | yes |
| variance_duration.environmental_conditions | 0.2 | 0.5% | decreasing | 0.6 | 0.6% | decreasing |  |
| variance_duration.ego_maneuver | 0.1 | 0.4% | increasing | 0.3 | 0.3% | decreasing |  |
| variance_duration.triggering_conditions | 0.2 | 0.7% | decreasing | 0.3 | 0.3% | decreasing |  |
| rarity_proportions_shape | 0.2 | 0.7% | categorical | 0.1 | 0.1% | categorical | yes |
| hidden_triggering_enabled | 0.0 | 0.0% | n/a | 0.0 | 0.0% | n/a |  |

## How to read the ranking

- **High SNR, clear trend** -> the parameter drives that output; the trend column says which direction.
- **SNR at or below ~1** -> the sweep stayed inside the seed-noise band; no effect distinguishable from randomness at this mileage and replicate count.
- Categorical factors (rarity/base-weight shapes, toggles, conditional mode) report SNR and percent effect but no numeric trend.
- `transition_mode_conditional` is a **structural** variant: turning on conditional mode also requires disabling full-scenario unknowns. Compare it against the standalone `full_scenario_enabled=off` row to isolate the conditional coupling's own contribution.

## Per-factor detail

### fixed_unknown_weight

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| fixed_0.0005 | 5/5 | 18234 | 0.437% | 17.3 | 8.86 | 899/82/35486 |
| fixed_0.001 | 5/5 | 18711 | 0.469% | 18.1 | 9.09 | 1369/202/35850 |
| fixed_0.005 | 5/5 | 22667 | 0.775% | 24.6 | 7.51 | 8214/1020/36100 |

### target_unknown_element_probability

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 0.001 | 5/5 | 22855 | 0.815% | 25.7 | 7.41 | 8403/1235/36072 |
| 0.002 | 5/5 | 27629 | 1.219% | 31.8 | 6.29 | 16712/2470/36077 |
| 0.008 (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |
| 0.016 (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |

- `0.008` infeasible: ConfigError: Layer 'temporal_modifications': element count n=30 in the configured range is infeasible: Calculated unknown weight (0.0498118) is not smaller than the very_rare weight (0.03). Fix this by one of: (1) increase the proportion of unknown elements, (2) lower target_unknown_element_probability, or (3) use unknown_weight_mode='fixed'.
- `0.016` infeasible: ConfigError: Layer 'temporal_modifications': element count n=30 in the configured range is infeasible: Calculated unknown weight (0.100434) is not smaller than the very_rare weight (0.03). Fix this by one of: (1) increase the proportion of unknown elements, (2) lower target_unknown_element_probability, or (3) use unknown_weight_mode='fixed'.

### average_speed_mph

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 25 | 5/5 | 73989 | 2.029% | 39.7 | 4.93 | 66621/9810/71547 |
| 75 | 5/5 | 24713 | 2.023% | 39.5 | 5.00 | 22059/3307/24061 |
| 100 | 5/5 | 18520 | 2.022% | 39.5 | 5.16 | 16573/2471/17996 |

### full_scenario_target_mass

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 0.002 | 5/5 | 28202 | 1.836% | 47.2 | 3.04 | 33246/4931/18226 |
| 0.008 | 5/5 | 55221 | 2.440% | 31.9 | 7.08 | 33246/4931/72266 |

### mean_duration.ego_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 54688 | 2.019% | 26.7 | 6.61 | 52914/4956/51507 |
| x2 | 5/5 | 27793 | 2.020% | 52.6 | 4.07 | 23254/4916/27415 |

### allow_self_transition

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| off | 5/5 | 54306 | 2.444% | 32.6 | 6.52 | 40022/4995/63596 |

### full_scenario_enabled

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| off | 5/5 | 19089 | 1.635% | 62.1 | 0.98 | 33246/4931/0 |

### transition_mode_conditional

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| conditional | 5/5 | 19630 | 1.657% | 61.3 | 1.01 | 34329/4931/0 |

### mean_duration.ru_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 48803 | 2.019% | 29.9 | 6.04 | 45574/4924/47107 |
| x2 | 5/5 | 31072 | 2.031% | 47.3 | 4.42 | 27034/4930/30180 |

### concentration_scale

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 1000 | 5/5 | 33666 | 1.857% | 39.8 | 5.53 | 28118/3554/35661 |
| 5000 | 5/5 | 37453 | 2.048% | 39.6 | 4.65 | 33695/4965/36245 |
| 100000 | 5/5 | 36699 | 1.988% | 39.2 | 4.79 | 32526/4811/36061 |

### mean_duration.triggering_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 41681 | 2.032% | 35.3 | 5.68 | 33218/9843/40301 |
| x2 | 5/5 | 34523 | 2.032% | 42.6 | 4.96 | 33309/2487/33249 |

### min_duration_seconds

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 0.001 | 5/5 | 37089 | 2.045% | 39.9 | 4.88 | 33296/4969/35913 |
| 0.5 | 5/5 | 36888 | 2.024% | 39.7 | 4.64 | 33224/4979/35573 |
| 5 | 5/5 | 37253 | 2.037% | 39.6 | 5.10 | 33266/4991/36250 |
| 30 | 5/5 | 32182 | 2.028% | 45.6 | 4.35 | 28096/4837/31431 |

### element_count.temporal_modifications

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| n30 | 5/5 | 36747 | 1.956% | 38.5 | 4.53 | 32495/4742/36256 |
| n46 | 5/5 | 36247 | 1.947% | 38.9 | 4.67 | 32460/4398/35637 |

### element_count.triggering_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| n50 | 5/5 | 37107 | 2.025% | 39.5 | 5.09 | 33246/4793/36175 |
| n75 | 5/5 | 37096 | 2.028% | 39.6 | 4.93 | 33246/4884/36061 |
| n100 | 5/5 | 37121 | 2.013% | 39.2 | 4.91 | 33246/4650/36347 |
| n150 | 5/5 | 36991 | 1.999% | 39.1 | 4.97 | 33246/4500/36235 |

### variance_duration.temporal_modifications

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 37244 | 2.025% | 39.4 | 5.01 | 33269/4900/36319 |
| x4 | 5/5 | 37314 | 2.056% | 39.9 | 5.34 | 33304/4945/36379 |

### mean_duration.street

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 37902 | 2.009% | 38.4 | 4.57 | 33285/4871/37649 |
| x2 | 5/5 | 36502 | 2.037% | 40.4 | 5.20 | 33363/4967/34673 |

### element_count.environmental_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| n15 | 5/5 | 37092 | 2.009% | 39.2 | 5.12 | 33246/4569/36368 |
| n21 | 5/5 | 37133 | 2.008% | 39.1 | 5.07 | 33246/4545/36475 |

### mean_duration.temporal_modifications

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 38185 | 2.032% | 38.5 | 4.95 | 34257/4906/37207 |
| x2 | 5/5 | 36719 | 2.019% | 39.8 | 4.99 | 32767/4901/35771 |

### element_count.ego_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| n7 | 5/5 | 37355 | 2.049% | 39.7 | 4.86 | 34143/4751/35816 |
| n12 | 5/5 | 37433 | 2.026% | 39.2 | 5.22 | 33478/4794/36595 |

### element_count.ru_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| n7 | 5/5 | 36747 | 2.013% | 39.6 | 5.26 | 33314/4650/35530 |
| n12 | 5/5 | 37374 | 2.014% | 39.0 | 5.27 | 33781/4543/36424 |

### mean_duration.environmental_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.5 | 5/5 | 37360 | 2.028% | 39.3 | 4.49 | 33222/4933/36566 |
| x2 | 5/5 | 37353 | 2.049% | 39.7 | 6.49 | 33348/4961/36396 |

### variance_duration.ru_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 36928 | 2.026% | 39.7 | 4.80 | 33276/4960/35620 |
| x4 | 5/5 | 37291 | 2.045% | 39.7 | 5.48 | 33351/4935/36296 |

### variance_duration.street

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 36975 | 2.018% | 39.5 | 4.91 | 33232/4956/35761 |
| x4 | 5/5 | 37246 | 2.029% | 39.4 | 5.53 | 33301/4987/36204 |

### unknown_proportion

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| 0.05 (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |
| 0.2 | 5/5 | 37524 | 2.020% | 39.0 | 4.44 | 34061/5047/35940 |

- `0.05` infeasible: ConfigError: Layer 'temporal_modifications': element count n=30 in the configured range is infeasible: Calculated unknown weight (0.0785542) is not smaller than the very_rare weight (0.03). Fix this by one of: (1) increase the proportion of unknown elements, (2) lower target_unknown_element_probability, or (3) use unknown_weight_mode='fixed'.

### base_weights_shape

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| flatter | 5/5 | 37136 | 2.022% | 39.4 | 5.25 | 33363/4910/35998 |
| steeper (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |

- `steeper` infeasible: ConfigError: Layer 'temporal_modifications': element count n=30 in the configured range is infeasible: Calculated unknown weight (0.0223534) is not smaller than the very_rare weight (0.008). Fix this by one of: (1) increase the proportion of unknown elements, (2) lower target_unknown_element_probability, or (3) use unknown_weight_mode='fixed'.

### variance_duration.environmental_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 37093 | 2.033% | 39.7 | 4.84 | 33325/4945/35917 |
| x4 | 5/5 | 36994 | 2.024% | 39.6 | 5.01 | 33333/4943/35712 |

### variance_duration.ego_maneuver

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 37071 | 2.042% | 39.9 | 4.92 | 33423/4980/35739 |
| x4 | 5/5 | 37214 | 2.041% | 39.7 | 4.84 | 33304/5008/36117 |

### variance_duration.triggering_conditions

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| x0.25 | 5/5 | 37242 | 2.035% | 39.6 | 4.57 | 33351/4965/36169 |
| x4 | 5/5 | 36981 | 2.030% | 39.7 | 5.38 | 33373/4928/35662 |

### rarity_proportions_shape

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| common_heavy (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |
| flat_known (5 infeasible) | 0/5 | n/a | n/a | n/a | n/a | n/a/n/a/n/a |
| tail_heavy | 5/5 | 36892 | 2.034% | 39.9 | 3.70 | 33369/4978/35437 |

- `common_heavy` infeasible: ConfigError: Layer 'temporal_modifications': element count n=30 in the configured range is infeasible: Calculated unknown weight (0.0304284) is not smaller than the very_rare weight (0.03). Fix this by one of: (1) increase the proportion of unknown elements, (2) lower target_unknown_element_probability, or (3) use unknown_weight_mode='fixed'.
- `flat_known` infeasible: ConfigError: Layer 'ego_maneuver': element count n=8 in the configured range yields zero unknown elements; shrink the range, raise the unknown proportion, or set allow_unknown: false.

### hidden_triggering_enabled

| level | feasible | episodes/Mmi | unknown-frac | episode dur (s) | dispersion | element/hidden/full episodes |
|---|:--:|---:|---:|---:|---:|---|
| baseline | 5/5 | 37166 | 2.035% | 39.6 | 4.87 | 33246/4931/36155 |
| off | 5/5 | 37176 | 2.035% | 39.6 | 4.87 | 38197/0/36155 |

## Method

- 67 variants (one baseline + 66 single-factor changes), each run for 5 independent seed sets at 2,000,000 miles: 335 full histories.
- A replicate offsets all seven simulator seeds and the full-scenario calibration seed by the same per-replicate amount, so replicates are independent whole-model histories.
- Per-layer durations were swept multiplicatively around each layer's own baseline (mean x0.5/x2, variance x0.25/x4). Element counts were pinned (min==max) at values in/around the researched ranges.
- Infeasible configurations (e.g. an unknown weight that would exceed the very-rare weight) are caught per run and reported, never silently dropped.
- Signal-to-noise = effect range across a factor's levels divided by the baseline seed standard deviation. No significance threshold is imposed; choose one from the tables and the noise band.
- Total wall time: 35.0 minutes on 12 worker processes.

## Files

- `run_rows.csv` - every individual run (all metrics, feasibility).
- `factor_summary.csv` - per factor x level aggregates (mean/sd/min/max).
- `sensitivity_ranking.csv` - effect range, percent, SNR and trend per factor.
- `summary.json` - full manifest and aggregates.
- `sensitivity_tornado.png` - SNR ranking for the two primary metrics.
- `response_curves.png` - metric response to each numeric factor.
- `runs/<factor>/<level>/replicate_*/stats.json` - full per-run output.
