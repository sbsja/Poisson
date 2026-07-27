# Duration-distribution study for `ego_008`

## Outcome

Changing the duration distribution mainly changes the **tail of episode duration**, not how often the element is selected. All four candidates have the same theoretical 30-second mean and 400 s² variance, so their average occupancy remains close; their rare long-duration behavior is different.

Across candidates, mean target-episode counts differed by only 0.8%, while mean target occupancy differed by 0.8%. The largest average 99th-percentile episode duration came from **Lognormal** at 103.2 seconds, versus 95.5 seconds for the current Gamma model.

**Recommendation:** retain Gamma as the neutral production default unless measured maneuver-duration data supports another family. Use Lognormal or Inverse Gaussian as tail-stress alternatives when the safety question is sensitivity to unusually long maneuvers; use Weibull when completion likelihood is expected to change with elapsed time.

## Aggregate simulation results

Each cell is the mean across three full runs; `±` is sample standard deviation.

| distribution | target episodes | episode mean | episode p90 | episode p99 | target occupancy | all unknown episodes | union unknown time |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gamma (current) | 20,901 ± 62 | 30.18 ± 0.17 s | 57.1 ± 0.3 s | 95.5 ± 0.6 s | 0.438% ± 0.004% | 75,932 ± 985 | 2.053% ± 0.009% |
| Weibull | 21,023 ± 73 | 30.20 ± 0.18 s | 57.8 ± 0.3 s | 91.5 ± 0.3 s | 0.441% ± 0.001% | 76,084 ± 390 | 2.049% ± 0.030% |
| Lognormal | 20,934 ± 103 | 30.18 ± 0.18 s | 54.7 ± 0.4 s | 103.2 ± 1.0 s | 0.439% ± 0.005% | 75,706 ± 156 | 2.036% ± 0.004% |
| Inverse Gaussian | 21,060 ± 21 | 30.19 ± 0.17 s | 55.8 ± 0.3 s | 103.1 ± 0.5 s | 0.442% ± 0.003% | 75,909 ± 422 | 2.035% ± 0.019% |

## Why these distributions

- **Gamma (current):** current positive waiting-time model; moderate right tail.
- **Weibull:** time-to-completion model with an elapsed-time-dependent hazard.
- **Lognormal:** multiplicative delays; allows occasional long maneuvers.
- **Inverse Gaussian:** first-passage/completion-time model with a strong right tail.

## Method

- Target: `ego_008`, the sole unknown ego-maneuver element in the current seeded configuration.
- 12 end-to-end simulations: four distributions × three duration seeds.
- Every run used the full configured 2,000,000-mile target.
- Only `ego_008` used the candidate distribution. Every other element retained the production Gamma model.
- Candidate durations were generated from common uniform quantiles using a dedicated target-element seed. This prevents target draws from consuming the shared duration RNG used by other elements.
- All candidates use theoretical mean 30 seconds and variance 400 s², followed by the simulator's existing one-second lower clamp.
- The production simulator and root configuration were not modified; the adapter exists only in this study runner.
- Total study wall time: 9.5 minutes.

## Files

- `runs.csv`: one row per simulation.
- `summary.csv`: distribution-level means, standard deviations, minima, and maxima.
- `summary.json`: study manifest, fitted parameters, per-run results, and aggregate results.
- `runs/.../stats.json`: compact output for each individual run.
- `duration_distribution_effects.png`: distribution shapes and outcome comparison.
