# Window-size and total-mileage study

## Outcome

The two settings affect different things:

- **Total simulated miles affects statistical stability.** Short runs produce valid results, but episode rates, unknown-time fractions, and dispersion estimates vary more between random histories.
- **Window size does not change the simulation outcome.** It changes how episode starts are grouped, so it changes the measured dispersion and the number of independent windows available for estimating it.

Using the explicit study rule—mean rate error no more than 2% from the same run's 2M-mile result, unknown-time error no more than 0.10 percentage point, and at least 30 default windows—the smallest tested distance that passed was **500,000 miles**.

At 2M miles, the current 10,000-mile window supplies 200 windows and measured dispersion 4.79 ± 0.69. A 100,000-mile window supplies only 20 windows. Its observed across-run variation was 7.7%, but 20 observations remain too few for a robust variance estimate.

In these five full histories, the 1,000- and 5,000-mile windows produced the most repeatable dispersion estimates. The current 10,000-mile window remains a practical balance: 200 observations, hundreds of episodes per window, and less granular reporting than the smaller alternatives.

**Recommendation:** keep the existing 2,000,000-mile target and 10,000-mile window for final reporting. For exploratory runs, use at least the precision distance identified above. Keep at least 30 complete windows when interpreting dispersion; for short runs, reduce window size rather than accepting only a handful of windows.

## Effect of total mileage

Each cell is the mean across five histories; `±` is sample standard deviation.

| simulated miles | episodes | episodes/M mile | rate error vs 2M | unknown-time fraction | unknown-time error | 10k windows | 10k dispersion |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 3,769 ± 156 | 37,686 ± 1,556 | 3.08% | 2.031% ± 0.055% | 0.044 pp | 10 | 4.77 ± 2.36 |
| 200,000 | 7,631 ± 236 | 38,157 ± 1,182 | 2.32% | 2.042% ± 0.016% | 0.021 pp | 20 | 4.59 ± 1.44 |
| 500,000 | 19,078 ± 383 | 38,157 ± 765 | 1.65% | 2.051% ± 0.024% | 0.013 pp | 50 | 4.43 ± 0.95 |
| 1,000,000 | 37,906 ± 691 | 37,906 ± 691 | 0.66% | 2.055% ± 0.025% | 0.008 pp | 100 | 4.68 ± 0.81 |
| 2,000,000 | 75,833 ± 742 | 37,916 ± 371 | 0.00% | 2.052% ± 0.015% | 0.000 pp | 200 | 4.79 ± 0.69 |

## Effect of window size at 2M miles

| window size | complete windows | mean episodes/window | dispersion | dispersion variation across runs | enough windows? |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 2000 | 37.9 | 4.83 ± 0.22 | 4.6% | yes |
| 5,000 | 400 | 189.6 | 4.99 ± 0.43 | 8.7% | yes |
| 10,000 | 200 | 379.2 | 4.79 ± 0.69 | 14.4% | yes |
| 25,000 | 80 | 947.9 | 5.15 ± 1.28 | 24.8% | yes |
| 50,000 | 40 | 1895.8 | 5.34 ± 1.46 | 27.3% | yes |
| 100,000 | 20 | 3791.6 | 4.80 ± 0.37 | 7.7% | no |

## Method

- Five independent runtime histories were simulated to the full 2,000,000-mile target.
- Transition vectors, element counts, rarity assignments, and full-scenario calibration were held fixed. Duration, initial-state, and transition-sampling seeds varied by history.
- The 100k, 200k, 500k, and 1M-mile results are exact prefixes of each corresponding 2M-mile history, which isolates the effect of observing less mileage.
- Window statistics use complete, non-overlapping windows and sample variance. Dispersion is variance divided by mean episode count.
- One-window cases are reported without dispersion because variance cannot be estimated from one observation.
- Prefix unknown-time fractions merge all overlapping episode intervals and clip intervals at the prefix boundary.
- Total simulation wall time: 4.2 minutes.

## Files

- `mileage_runs.csv` and `mileage_summary.csv`: per-history and aggregate mileage results.
- `window_runs.csv` and `window_summary.csv`: the complete mileage/window grid.
- `summary.json`: manifest, per-run metadata, and aggregate results.
- `runs/.../stats.json`: compact output for each independent full history.
- `window_mileage_effects.png`: convergence and window-scale comparison.
