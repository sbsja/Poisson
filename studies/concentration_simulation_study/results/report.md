# Concentration sensitivity — full simulation study

## Result

Increasing `concentration_scale` does not change the designed unknown mass (0.4% per unknown-bearing layer); it reduces how far each one-time Dirichlet draw can wander from that target. That initialization effect propagates to episode counts and the fraction of simulated time classified as unknown.

In this empirical sweep, **c = 20,000** was the smallest tested value for which every unknown-bearing layer in all 3 runs stayed within ±25% of its target.

The current `c = 20,000` remains a sensible production setting: it materially suppresses seed-to-seed initialization error without requiring a near-deterministic transition vector. The three-run sample is a sensitivity demonstration, not a replacement for the larger Monte Carlo calibration in the project's original `concentration_study.md`.

## Aggregate results

Each cell is the mean across three runs; `±` is the sample standard deviation.

| concentration | worst layer error | element-route episodes | full-scenario episodes | total episodes | unknown-time fraction | runs within ±25% |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 144.7% ± 77.4% | 12,533 ± 1,231 | 36,432 ± 584 | 48,964 ± 1,093 | 1.392% ± 0.604% | 0/3 |
| 1,000 | 51.9% ± 13.7% | 34,732 ± 8,919 | 36,030 ± 534 | 70,762 ± 9,045 | 1.757% ± 0.232% | 0/3 |
| 5,000 | 24.2% ± 8.0% | 34,901 ± 6,773 | 36,321 ± 711 | 71,222 ± 7,482 | 1.857% ± 0.258% | 2/3 |
| 20,000 | 12.4% ± 4.3% | 36,289 ± 3,484 | 36,787 ± 632 | 73,075 ± 3,746 | 1.935% ± 0.145% | 3/3 |
| 100,000 | 6.4% ± 1.6% | 36,329 ± 1,113 | 37,080 ± 850 | 73,409 ± 1,963 | 1.942% ± 0.062% | 3/3 |

## What changed

- At `c = 100`, the worst layer's mass error ranged from 99.0%–234.0% across the three transition-vector draws.
- At the current `c = 20,000`, that range narrowed to 9.2%–17.3%.
- At `c = 100,000`, it narrowed further to 4.7%–7.9%, showing diminishing returns once the vector is already tightly centered on the designed weights.
- Full-scenario rarity is recalibrated to 0.4% stationary mass for each constructed model, so its episode count is less directly tied to the unknown-element mass than the element-route count is.

## Method

- 15 end-to-end simulations: five concentrations × 3 transition-vector seeds.
- Every run used the full configured 2,000,000-mile target and all features enabled in the root `config.yaml`.
- Element counts, rarity assignment, durations, initial-state, and transition-sampling seeds were held fixed. Only the Dirichlet `transition_matrix` seed varied by replicate.
- Error means `abs(realized_mass - 0.004) / 0.004`; the reported worst error is the maximum across the four unknown-bearing layers.
- Total study wall time: 9.1 minutes.

## Files

- `runs.csv`: one row per simulation.
- `summary.csv`: concentration-level means, standard deviations, minima, and maxima.
- `summary.json`: machine-readable manifest plus all per-run and aggregate data.
- `runs/.../stats.json`: compact result for each individual simulation.
- `concentration_effects.png`: visual comparison of the principal outcomes.
