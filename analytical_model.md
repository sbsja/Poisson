# Analytical Expected Results (no simulation)

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

## Combination episodes (conditional predictions)

| rule | mass | E[episodes] | E[duration] (s) |
|---|---|---|---|
| street=forced_merge_merging & environmental_conditions=environment_000 | 0.0696% | 382.6 | 262.0 |
| street=lane_split_proceeding & temporal_modifications=temporal_024 | 0.2684% | 1,815.6 | 212.9 |
| street=lane_split_exiting & triggering_conditions=trigger_066 | 0.0328% | 539.5 | 87.6 |
| temporal_modifications=temporal_000 & environmental_conditions=environment_007 | 0.2549% | 778.8 | 471.3 |
| (hash, threshold 0.005) | - | 42,055.5 | 16.8 |

Pattern-rule formulas: E[episodes] = T*mass*hazard with hazard = sum over referenced layers of (1-q)/mu; E[duration] = 1/hazard. Hash: E[episodes] = T * tuple-change-rate * P(all known) * threshold; E[duration] = 1/tuple-change-rate.

## Headline predictions vs the delivered 2M-mile run

| quantity | design (a priori) | conditional (this config) | simulated |
|---|---|---|---|
| total unknown episodes | 83,221 | 84,724 | 84,296 |
| episodes per 1M miles | 41,610.5 | 42,361.9 | 42,148.0 |
| mean episode duration (s) | 47.0 | 47.0 | 47.2 |
| total unknown time (s, union) | 2,290,213 | 2,359,833 | 3,946,822 |
| unknown-time fraction (%) | 1.590 | 1.639 | 2.741 |
| inter-arrival mean (mi) | 24.0 | 23.6 | 23.7 |
| inter-arrival median (mi) | 16.7 | 16.4 | 16.1 |
| inter-arrival p90 (mi) | 55.3 | 54.4 | 55.6 |
| mean episode starts / 10k-mi window | 416.1 | 423.6 | 421.5 |
| dispersion index | 1.000 | 1.000 | 1.261 |

Per-layer episode counts, conditional prediction vs simulated: temporal_modifications 977 vs 977; ego_maneuver 20,881 vs 21,018; ru_maneuver 12,260 vs 12,217; triggering_conditions 5,033 vs 5,015

Expected statistical noise on the episode count is ~sqrt(N) = 291; the simulated total should (and does) fall within a few sigma of the conditional prediction.

## What the closed forms do and do not cover

- Covered exactly (in expectation): transition counts, episode counts, mean durations, per-layer and total unknown time, the union fraction, rates per mile, window means, inter-arrival moments and (approximately) their exponential distribution.
- Approximations: episode starts are treated as Poisson (superposition of thinned renewal processes) - excellent for small unknown mass; the Gamma-regularity of the driving renewals makes the true dispersion slightly below 1 (simulated ~0.96). The min_duration clamp (1 s vs means of 30-1800 s) is ignored - a per-mille effect.
- Not covered by closed forms: extreme-value quantities (the maximum episode duration / longest gap), the exact per-seed realization (theory predicts expectations, the simulator one concrete draw), and any future non-renewal extensions (e.g. unknown combinations tied to full tuples, conditional probabilities between layers).

The two prediction levels differ because the design level assumes every layer hits the 0.4% target exactly, while the built layers carry the (now small, c=20,000) Dirichlet scatter of their realized unknown mass.
