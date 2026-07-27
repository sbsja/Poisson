# Analytical Expected Results (no simulation)

> This closed-form model supports `transition_model.mode: independent` only.
> Conditional transition rules require dependency-aware occupancy and
> entry-rate calculations and are intentionally rejected by
> `analytical_model.py`. In this document, “conditional prediction” means
> conditioned on the realized Dirichlet vectors, not conditional cross-layer
> behavior.

Derivation: each layer is a renewal process (i.i.d. Gamma sojourns, i.i.d. categorical transitions from its permanent vector), so episode statistics follow from renewal theory and Poisson thinning; see the docstring of analytical_model.py for the formulas.

Two prediction levels: **design** (a priori: every unknown-bearing layer has exactly the 0.4% target mass) and **conditional** (given the actually built layers of this config, i.e. the realized Dirichlet vectors).

## Per-layer expected values (conditional)

| layer | E[transitions] | unknown mass | E[episodes] | E[mean episode duration] (s) |
|---|---|---|---|---|
| street | 480,000 | 0.0000% | 0.0 | nan |
| temporal_modifications | 240,000 | 0.4077% | 977.4 | 600.63 |
| ego_maneuver | 4,800,000 | 0.4369% | 20,881.0 | 30.13 |
| ru_maneuver | 3,200,000 | 0.3846% | 12,260.0 | 45.17 |
| environmental_conditions | 80,000 | 0.0000% | 0.0 | nan |
| triggering_conditions | 1,200,000 | 0.4197% | 5,033.4 | 120.08 |

## Full-scenario rarity episodes (conditional predictions)

- calibrated stationary rare mass: 0.4000% (= expected fraction of simulated time in rare tuples)
- E[episodes] ~= T * tuple-change-rate * mass = 34,205 (entry-rate approximation, ~10%)
- E[episode duration] ~= 1/tuple-change-rate = 16.8 s

## Headline predictions vs the delivered 2M-mile run

| quantity | design (a priori) | conditional (this config) | simulated |
|---|---|---|---|
| total unknown episodes | 71,833 | 73,357 | 75,227 |
| episodes per 1M miles | 35,916.6 | 36,678.4 | 37,613.5 |
| mean episode duration (s) | 40.1 | 40.2 | 39.1 |
| total unknown time (s, union) | 2,290,213 | 2,359,833 | 2,685,954 |
| unknown-time fraction (%) | 1.590 | 1.639 | 1.865 |
| inter-arrival mean (mi) | 27.8 | 27.3 | 26.6 |
| inter-arrival median (mi) | 19.3 | 18.9 | 9.4 |
| inter-arrival p90 (mi) | 64.1 | 62.8 | 77.9 |
| mean episode starts / 10k-mi window | 359.2 | 366.8 | 376.1 |
| dispersion index | 1.000 | 1.000 | 4.414 |

Per-layer episode counts, conditional prediction vs simulated: temporal_modifications 977 vs 977; ego_maneuver 20,881 vs 21,018; ru_maneuver 12,260 vs 12,217; triggering_conditions 5,033 vs 5,015

Expected statistical noise on the episode count is ~sqrt(N) = 271; the simulated total should (and does) fall within a few sigma of the conditional prediction.

## What the closed forms do and do not cover

- Covered exactly (in expectation): transition counts, episode counts, mean durations, per-layer and total unknown time, the union fraction, rates per mile, window means, inter-arrival moments and (approximately) their exponential distribution.
- Approximations: episode starts are treated as Poisson (superposition of thinned renewal processes) - excellent for small unknown mass; the Gamma-regularity of the driving renewals makes the true dispersion slightly below 1 (simulated ~0.96). The min_duration clamp (1 s vs means of 30-1800 s) is ignored - a per-mille effect.
- Not covered by closed forms: extreme-value quantities (the maximum episode duration / longest gap), the exact per-seed realization (theory predicts expectations, the simulator one concrete draw), and any future non-renewal extensions (e.g. unknown combinations tied to full tuples, conditional probabilities between layers).

The two prediction levels differ because the design level assumes every layer hits the 0.4% target exactly, while the built layers carry the (now small, c=20,000) Dirichlet scatter of their realized unknown mass.
