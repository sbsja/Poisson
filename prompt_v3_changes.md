# Change Request v3 — Full-Scenario Rarity Unknowns

Third change-request document, following the original assignment (v1,
specified in chat) and `prompt_v2_changes.md` (v2: episode semantics,
fixed street layer, element-count research, concentration study; its §8
addendum reintroduced hash + pattern combinations). *Version-numbering
note:* README/DOCUMENTATION label the resulting configurations
chronologically (v3 = combinations re-enabled, v4 = this change); as a
change-request document this is the third, hence the file name.

**Status: IMPLEMENTED** — 46 tests passing, 2M-mile run delivered in
`results_full_scenario/` (see Results at the end).

---

## Task

Implement rare unknown scenarios as complete six-layer tuples.

## Context

- Pattern-based unknown scenarios are disabled.
- Hash combinations are disabled.
- Keep existing element-level unknown episodes unchanged.
- Add a new unknown-scenario mechanism based on the rarity of the
  complete scenario, not a subset of layers.

## Definition

A scenario is the exact tuple

    (street, temporal_modifications, ego_maneuver, ru_maneuver,
     environmental_conditions, triggering_conditions)

For the current tuple S, its stationary probability is

    P(S) = P(street element) * P(temporal element) * P(ego element)
         * P(road-user element) * P(environment element)
         * P(triggering-condition element)

using each layer's realized permanent `transition_probs`. A tuple is an
unknown scenario when

    P(S) <= calibrated_rarity_threshold

Do not use SHA-256 hashing. Do not use partial-layer pattern rules.
Every classification must use all six current layers.

## Configuration

```yaml
full_scenario_unknowns:
  enabled: true
  target_stationary_mass: 0.004     # desired probability MASS of rare tuples
  calibration_samples: 2000000
  calibration_seed: 90123           # dedicated, reproducible
```

- `target_stationary_mass` is the desired probability mass of all tuples
  classified as unknown scenarios (0.004 = 0.4% of simulated time in
  expectation).
- `calibrated_rarity_threshold` is determined at initialization so that
  sum(P(S) for all S with P(S) <= threshold) ≈ target_stationary_mass.
- Coverage is measured in total probability mass, never in the number of
  rare tuples.
- A dedicated RNG/seed performs the calibration so that element-count,
  rarity, transition-matrix, duration, initial-state, and
  transition-sampling randomness are untouched.
- Calibration is deterministic Monte Carlo from the six transition
  vectors: N tuples are drawn from the stationary product distribution;
  because the samples come from P itself, the mass of {P <= t} equals the
  fraction of samples below t, so the threshold is the target-quantile of
  the sampled P values. The approximation is documented (in-sample mass
  exact to ~1/N; true mass of the thresholded set carries the MC quantile
  error ~ sqrt(target·(1−target)/N) ≈ 1.1% relative at the defaults), and
  the achieved sampled mass is reported.

## Episode semantics

- New episode type `full_scenario`.
- The full tuple is evaluated once per event, after all simultaneously
  expired layers are updated.
- At t = 0, open a full-scenario episode if the initial tuple is rare.
- Known tuple → rare tuple: open an episode.
- Rare tuple → known tuple: close the episode.
- Rare tuple A → rare tuple B: close A and open B at the same timestamp
  (the exact scenario changed).
- A self-transition that leaves the complete tuple unchanged must not
  split an episode.
- Any genuine change in any of the six layers changes the full tuple.
- Full-scenario episodes may overlap element-level unknown episodes; the
  union unknown time counts overlaps only once.

## Outputs

- Calibrated threshold, target stationary mass, calibration sample count,
  and achieved estimated mass in `stats.json` and `summary.md`.
- Number of full-scenario episodes and their duration statistics.
- Full-scenario episodes in `episodes.csv` with `type = full_scenario`,
  `layer = scenario`, `element =` pipe-separated six-layer tuple.
- Plots and the analytical-model documentation updated (expected time
  fraction = calibrated mass; E[duration] ≈ 1/tuple-change-rate;
  E[episodes] ≈ T · tuple-change-rate · mass, entry-rate approximation
  ~10%).
- Historical results (`results/`) are explicitly marked as not valid for
  the new configuration until regenerated.

## Validation and tests

- Validate: target mass in (0, 1); calibration samples sufficiently large
  (≥ max(100000, 10/target)); calibration seed an integer; no unknown
  keys in the block.
- Tests: reproducible calibrated threshold (and independence from the
  other seed streams); no hash or pattern episode creation; classification
  uses all six layers; rare A → rare B closes and opens separate episodes;
  tuple self-transition continuity; union-time correctness with
  overlapping element and full-scenario episodes (independent
  interval-merge comparison); calibration mass within 3/N of the target.
- Checkpoint/resume remains bit-identical.

## Results (delivered run, `results_full_scenario/`)

- Calibrated threshold 5.691e-10 (target mass 0.4000%, achieved sampled
  mass 0.4000%, N = 2,000,000, seed 90123).
- 75,227 episodes total: 39,227 element (bit-identical to the previous
  run — the mechanism consumes no simulation randomness) + 36,000
  full-scenario (mean duration 15.8 s ≈ mean tuple lifetime, median
  12.6 s, max 163.2 s, none truncated).
- **Realized full-scenario unknown mass: 0.3938% of simulated time vs the
  0.4000% configured target.**
- Analytical prediction 73,357 total episodes vs 75,227 simulated; the
  gap sits in the documented ~10% entry-rate approximation for
  full-scenario episode counts (the time-fraction prediction is exact in
  expectation).
