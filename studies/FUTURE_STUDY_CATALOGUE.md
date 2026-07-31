# Comprehensive Future Study Catalogue

**Status: planning only. Do not run these studies until the simulator redesign is complete, reviewed, and a new baseline configuration is frozen.**

This document is the master plan for studying how every configurable part of
the simulator affects its outputs. It is exhaustive with respect to the
current configuration surface and also identifies high-value studies that
would require new configuration options. Numerical parameters have infinitely
many possible values, so “every possible study” means every parameter,
mechanism, construction choice, seed stream, scientifically meaningful
interaction, boundary condition, and important non-configured extension—not
literally every real number or every possible rule graph.

The concentration, single-element duration-family, and mileage/window studies
already present under `studies/` describe the pre-redesign simulator. They must
be treated as historical evidence and rerun after the redesign if their
conclusions are still needed.

## 1. Study gate and baseline requirements

No sensitivity result is meaningful while simulator behavior is changing.
Before beginning this catalogue:

1. Freeze a versioned baseline configuration and simulator commit.
2. Record the exact semantic catalogue version for every layer.
3. Define the episode semantics and unknown-scenario routes in one normative
   document.
4. Pass unit, reproducibility, checkpoint/resume, and time/mileage consistency
   tests.
5. Generate a baseline analytical prediction where one is available.
6. Run at least five identical-seed repeats and verify bit-identical outputs.
7. Choose standard screening and confirmation mileages only after benchmarking
   the redesigned simulator.
8. Store every study's complete configuration, simulator version, seed set,
   wall time, and result schema with its outputs.

The post-redesign baseline—not today's `config.yaml`—must be the control for
all future comparisons.

## 2. Outcomes to measure in every study

Every study should record the same core responses so that results can be
compared across study families.

### 2.1 Exposure and episode outcomes

- Total unknown episodes and episodes per million miles.
- Counts by route and type: visible element, hidden triggering condition,
  pattern, hash combination, and full-scenario rarity.
- Counts by layer and, where useful, by element.
- Unknown union time in seconds and as a fraction of simulated time.
- Per-layer unknown occupancy fraction.
- Episode duration mean, median, p90, p95, p99, p99.9, maximum, and truncated
  fraction, in both seconds and miles.
- Inter-arrival distance/time mean, median, p90, p99, and maximum.
- Number and duration of overlapping episodes; maximum simultaneous episodes.
- Transition counts, empirical selection probabilities, self-transition
  frequency, and realized stationary masses.

### 2.2 Statistical stability outcomes

- Window-count mean, sample variance, dispersion, autocorrelation, and
  coefficient of variation at multiple window scales.
- Between-seed mean, standard deviation, confidence interval, and coefficient
  of variation for every primary response.
- Bias and absolute error relative to analytical predictions or a long-run
  reference.
- Convergence versus simulated mileage and number of replications.
- Tail uncertainty using bootstrap intervals or an extreme-value method.
- Probability that a run exceeds each operational risk threshold.

### 2.3 Calibration and fidelity outcomes

- Designed, realized, and empirical probability for each rarity and unknown
  category.
- Conditional-rule match, influence, and selection rates.
- Full-scenario target mass, achieved calibration mass, threshold, and
  out-of-sample achieved mass.
- Route composition error versus configured street probabilities.
- Duration sample mean/variance versus configured moments.
- Sensitivity of semantic elements and rarity categories, not only totals.

### 2.4 Computational outcomes

- Initialization, calibration, simulation, plotting, and serialization time.
- Events processed per second and miles simulated per second.
- Peak memory, episode-list size, output size, and checkpoint size.
- Scaling with mileage, catalogue size, rules, calibration samples, and number
  of enabled unknown mechanisms.

## 3. Standard wide sweep designs

Use these common grids unless a parameter-specific section provides a better
one. Always include the post-redesign baseline.

### 3.1 Positive scale parameters

For a baseline value `b`, screen:

`0.01b, 0.03b, 0.1b, 0.25b, 0.5b, 0.75b, b, 1.5b, 2b, 4b, 10b, 30b, 100b`

Remove invalid or physically impossible values, but record the rejected
boundary as a validation result.

### 3.2 Probabilities and target masses

Where feasible, screen:

`0, 10⁻⁶, 10⁻⁵, 10⁻⁴, 5×10⁻⁴, 0.001, 0.002, 0.004, 0.01, 0.025, 0.05, 0.10, 0.25, 0.50, 0.90, 0.99`

Zero and one are boundary tests and may intentionally fail validation. For
unknown-element targets, first calculate the valid maximum under the catalogue
and rarity-weight constraints, then add points at 50%, 80%, 95%, 99%, and 100%
of that maximum.

### 3.3 Integer counts

Use a log-spaced set plus values around important boundaries:

`1, 2, 3, 5, 7, 10, 15, 25, 50, 75, 100, 150, 250, 500, 1,000`

For sample counts use:

`10³, 10⁴, 10⁵, 5×10⁵, 10⁶, 2×10⁶, 5×10⁶, 10⁷, 5×10⁷`

### 3.4 Duration moment design

Study duration mean and shape separately. For each layer, combine mean
multipliers with coefficients of variation:

- Mean multiplier: `0.01, 0.03, 0.1, 0.25, 0.5, 1, 2, 4, 10, 30`.
- Coefficient of variation: `0.01, 0.05, 0.10, 0.25, 0.50, 0.67, 1, 2, 5`.
- Convert to variance using `variance = (CV × mean)²`.

This is clearer than varying raw variance without controlling the mean.

### 3.5 Replication levels

- Deterministic/invariance checks: 1 seed pair is sufficient, then repeat with
  3 additional seed sets.
- Wide screening: at least 5 independent runtime seeds per configuration.
- Confirmation: at least 20 seeds for shortlisted configurations.
- Rare-tail or exceedance estimates: 50–200 seeds or a justified sequential
  stopping rule.
- Construction variability: at least 100–1,000 cheap construction draws when
  no driving simulation is required.

Use common random numbers when possible: keep unrelated seed streams identical
between paired configurations. Report both conditional-on-construction and
unconditional-across-construction uncertainty.

## 4. Complete study catalogue

### A. Randomness, seeds, and reproducibility

#### RNG-01 — Individual seed-stream sensitivity

Vary each seed independently while holding every other seed fixed:

- `seeds.element_count`
- `seeds.rarity_assignment`
- `seeds.transition_matrix`
- `seeds.duration`
- `seeds.initial_state`
- `seeds.transition_sampling`
- `seeds.pattern_rules`
- `global_seed`
- `full_scenario_unknowns.calibration_seed`

Use consecutive seeds, widely separated seeds, zero, maximum supported integer,
and at least 100 random seeds. Separate construction-seed effects from runtime
seed effects.

#### RNG-02 — Seed-group decomposition

Compare four uncertainty definitions:

1. fixed construction and varying runtime;
2. varying construction and fixed runtime;
3. varying all streams together;
4. nested design: several runtime histories inside each constructed model.

This quantifies how much uncertainty comes from model construction versus
driving history.

#### RNG-03 — Seed independence and collision study

Test identical seed numbers across streams, consecutive numbers, large offsets,
randomly generated independent seeds, and deliberately repeated seeds. Verify
that independent streams do not accidentally become coupled.

#### RNG-04 — Reproducibility and execution-path invariance

Verify bit identity for repeated runs, single-shot versus checkpoint/resume,
different checkpoint wall limits, logging on/off, plots on/off, and equivalent
configuration key ordering. Test on every structural mode.

#### RNG-05 — Seed convergence

Estimate how conclusions change when using 3, 5, 10, 20, 50, 100, and 200
replicates. Determine the minimum replication count needed for each primary
metric and tail metric.

### B. Simulation horizon, speed, and output windows

#### RUN-01 — Total simulated mileage

Suggested grid:

`10³, 10⁴, 5×10⁴, 10⁵, 2×10⁵, 5×10⁵, 10⁶, 2×10⁶, 5×10⁶, 10⁷, 5×10⁷, 10⁸ miles`

Measure convergence, rare-event discovery, tail stability, runtime, memory, and
output size. Use exact prefixes of common long histories where valid.

#### RUN-02 — Average speed

Suggested grid:

`1, 5, 15, 30, 50, 70, 100, 150, 250 mph`

At fixed mileage, speed changes simulated time and therefore transition and
episode opportunities. Compare time-based and distance-based statistics.

#### RUN-03 — Minimum duration clamp

Suggested grid:

`10⁻⁶, 0.001, 0.01, 0.1, 0.5, 1, 2, 5, 10, 30, 60 seconds`

Record how frequently the clamp activates, the induced moment bias, event
rate, simultaneous expiry behavior, and runtime.

#### RUN-04 — Mileage window size

Suggested grid:

`10, 100, 500, 1k, 5k, 10k, 25k, 50k, 100k, 250k, 500k, 1M miles`

Always cross window size with total mileage. Require at least 30 complete
windows for a primary dispersion estimate and report sensitivity to window
alignment if that feature is added.

#### RUN-05 — Speed × duration × mileage equivalence

Test configurations with the same simulated time but different speed/mileage,
and configurations with the same mileage but different simulated time. Verify
which metrics are invariant in seconds and which are invariant in miles.

### C. Duration behavior

Run every duration study globally, one layer at a time, one rarity at a time,
and—after element-specific duration support exists—one element at a time.

#### DUR-01 — Per-layer mean duration

Apply the standard duration mean grid separately to street, temporal
modifications, ego maneuvers, road-user maneuvers, environmental conditions,
and triggering conditions. Then scale all layers together and study relative
time-scale ratios between layers.

#### DUR-02 — Per-layer duration variance/CV

Use the standard CV grid at fixed mean for every layer. Measure tail duration,
episode overlap, clustering, event rate, clamp frequency, and dispersion.

#### DUR-03 — Mean × CV interaction

Use the full mean-multiplier × CV grid for each layer. This is necessary
because the minimum clamp and heavy tails make mean and variance effects
non-additive.

#### DUR-04 — Distribution family

For moment-matched positive distributions compare:

- deterministic/constant;
- Gamma;
- Exponential;
- Erlang with multiple integer shapes;
- Weibull;
- Lognormal;
- Inverse Gaussian;
- Generalized Gamma;
- log-logistic;
- Pareto and truncated Pareto;
- uniform and triangular with valid positive support;
- scaled Beta with several bounds;
- two-point and finite discrete empirical distributions;
- mixtures of short/normal/long regimes;
- zero-inflated or near-zero mixtures if semantically valid;
- empirical resampling and fitted parametric distributions from real data.

Study each family at several means and CVs, not only one moment pair.

#### DUR-05 — Element- and rarity-specific duration models

Assign different duration laws to common, medium, rare, very-rare, and unknown
elements. Then test each semantic element individually, particularly every
unknown element and safety-critical maneuver.

#### DUR-06 — State-dependent and transition-dependent durations

If added to the redesign, compare durations conditioned on previous element,
next element, street context, environment, conditional-rule match, and unknown
status. Include hysteresis and duration-memory models.

#### DUR-07 — Correlated durations

If added, study positive and negative correlations between layer durations,
shared congestion/weather factors, autocorrelation within a layer, and common
shock events. Suggested correlations: `-0.9, -0.5, -0.2, 0, 0.2, 0.5, 0.9`.

#### DUR-08 — Initial-duration semantics

Compare a fresh duration draw at time zero, equilibrium residual-life
sampling, fixed initial residuals, and warm-up/burn-in periods. This can matter
for short runs and non-memoryless distributions.

### D. Layer construction and semantic catalogues

#### CAT-01 — Construction form

For non-street layers compare all supported forms:

- fixed elements with exact probabilities where permitted;
- versioned semantic catalogue;
- generated catalogue with `element_count_min/max`.

Compare the same effective probabilities across forms to identify construction
artifacts.

#### CAT-02 — Catalogue size by layer

For every non-street layer, test fixed sizes from the integer grid. For legacy
generated ranges, separately vary minimum, maximum, range width, and whether
the baseline count is near a range boundary.

#### CAT-03 — Catalogue composition

Add or remove one element at a time; remove each existing element in turn;
duplicate semantic roles under distinct IDs; merge similar elements; split one
element into 2, 5, 10, or 50 sub-elements; and add increasing numbers of rare
and unknown elements.

#### CAT-04 — Rarity assignment of every semantic element

Move each element through common, medium, rare, very-rare, and unknown where
semantically allowed. Study one-at-a-time changes, complete reassignment,
randomized assignments, and expert-defined alternative catalogues.

#### CAT-05 — Unknown-element count and fragmentation

At fixed total unknown probability, distribute that mass across 1, 2, 5, 10,
25, 50, and all available unknown elements. Measure episode fragmentation,
self-transition continuation, hidden-category behavior, and per-element tails.

#### CAT-06 — `allow_unknown` topology

Toggle `allow_unknown` for each eligible layer individually and test all valid
subsets of unknown-bearing layers. Include no unknown-bearing layer, each
single layer, all pairs, all triples, and all layers. Keep route definitions
explicit.

#### CAT-07 — Semantic metadata invariance

Change catalogue version strings, labels, and descriptions without changing
IDs or rarities. Dynamics should remain identical. Then change IDs while
preserving meaning: independent-mode dynamics should remain equivalent, but
hash classification and rules that reference IDs may change and must be
documented.

#### CAT-08 — Catalogue ordering invariance

Permute element order while preserving IDs, rarities, and probabilities. Test
whether results are distributionally invariant and whether same-seed bit
identity is expected. Include rule references and hash classification.

#### CAT-09 — Street route catalogue and probabilities

Study each street probability from near zero to dominant while renormalizing
the remainder. Compare current composition, uniform, one-route-dominant,
high-entropy, low-entropy, route-removal, route-addition, and empirically
perturbed profiles (`±1%, ±5%, ±10%, ±25%, ±50%` relative perturbations).

#### CAT-10 — Number and identity of layers

If the redesign makes layers configurable, test removing each layer, adding
new layers, duplicating a layer, and models with 1–12 layers. Measure both
statistical effects and event-loop scaling.

### E. Rarity, weights, and transition vectors

#### TRN-01 — Rarity-proportion simplex

Study broad compositions rather than varying one proportion without
renormalization:

- uniform across categories;
- common-dominant (80–99% common);
- medium-dominant;
- rare-tail-heavy;
- very-rare-heavy;
- unknown proportions from zero to the feasible maximum;
- Dirichlet/LHS samples across the full probability simplex;
- one category approaching zero and each valid simplex vertex.

Repeat for unknown-enabled and unknown-disabled layers because known
proportions are renormalized when unknowns are disabled.

#### TRN-02 — Base-weight ratios

Study common:medium:rare:very-rare ratios spanning equal weights through
orders-of-magnitude separation. Suggested normalized families include:

- `1:1:1:1`
- `1:0.75:0.5:0.25`
- `1:0.4:0.1:0.03` (current reference)
- `1:0.1:0.01:0.001`
- reversed and non-monotone profiles as robustness tests.

Multiply all base weights by common factors from `10⁻⁶` to `10⁶`; normalized
behavior should be invariant where the unknown-weight calculation scales
consistently.

#### TRN-03 — Unknown-weight mode

Compare `calculated` and `fixed` modes across every catalogue size, rarity
composition, and unknown-element count. Quantify designed-versus-realized mass
and feasibility failures.

#### TRN-04 — Target unknown-element probability

Use the broad probability grid plus dense points near the maximum feasible
target for each catalogue. Study each unknown-bearing layer separately if the
redesign adds per-layer targets, and compare a shared global target with
heterogeneous targets.

#### TRN-05 — Fixed unknown weight

Use `10⁻⁸` through `10²` on a log grid, subject to validation. Measure how
catalogue size and known-weight sum transform a fixed raw weight into actual
unknown probability.

#### TRN-06 — Dirichlet concentration

Use an extensive log grid:

`0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1k, 3k, 10k, 20k, 30k, 100k, 300k, 1M, 10M, 100M`

Measure construction-to-construction variance, near-zero probabilities,
entropy, target adherence, episode rates, and numerical stability.

#### TRN-07 — Self-transition policy

Compare `allow_self_transition=true/false`, then—if added—per-layer and
per-element policies, maximum consecutive self-transitions, sticky-state
multipliers, and explicit self-transition probabilities.

#### TRN-08 — Initial versus transition probabilities

Compare initial state drawn from designed weights, realized transition vector,
uniform distribution, fixed scenario, equilibrium distribution, and a warm-up
state. Study short-run bias and interaction with conditional initialization.

#### TRN-09 — Transition-matrix architecture extensions

If added, compare the current independent destination vector with full Markov
matrices, sparse adjacency graphs, forbidden transitions, distance-dependent
transitions, time-varying matrices, and semi-Markov state/transition-specific
sojourn models.

### F. Conditional transition rules

Full-scenario rarity is currently incompatible with conditional mode; every
conditional study must disable it unless dependency-aware calibration is
implemented.

#### COND-01 — Independent versus conditional mode

Start with no rules, then one rule at a time, all rules, and randomized valid
rule sets. Verify that conditional mode with no active effect is equivalent to
independent mode where expected.

#### COND-02 — Conditional initialization

Compare `apply_to_initial_state=true/false` for short and long runs, fixed and
random initial states, and shallow versus deep dependency graphs.

#### COND-03 — Rule multiplier strength

For both element and rarity multipliers use:

`0, 10⁻⁶, 10⁻⁴, 0.001, 0.01, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 4, 10, 100, 10⁴, 10⁶`

Include exact zero suppression, near-zero suppression, neutral multiplier one,
and extreme forcing. Measure normalization and zero-distribution failures.

#### COND-04 — Rule prevalence and selector breadth

Condition on each element and rarity separately, then selectors covering 1,
2, 5, 10, 25%, 50%, and all parent elements. Compare rare versus common
contexts and one-parent versus multi-parent AND conditions.

#### COND-05 — Target-layer and effect scope

Use every layer as target and every other layer as parent. Modify individual
elements, each rarity, unknown rarity, all known rarities, and mixed
element-plus-rarity effects.

#### COND-06 — Rule count and graph topology

Study 0, 1, 2, 5, 10, 25, 50, 100, 500, and 1,000 rules. Compare chains,
stars, trees, layered DAGs, dense DAGs, disconnected components, and maximum
valid dependency depth. Include cycles as validation tests.

#### COND-07 — Overlapping and conflicting rules

Create rules that reinforce, cancel, or suppress the same target element;
rules with overlapping selectors; and multiple simultaneously matched rules.
Test rule-order invariance and floating-point behavior under extreme products.

#### COND-08 — Conditional unknown amplification

Vary unknown multipliers by context to study localized risk. Measure global
unknown rate, conditional unknown rate, context prevalence, and whether a low
global average hides high-risk subpopulations.

#### COND-09 — Dynamic or lagged dependencies

If added, test rules based on previous states, time in state, recent history,
episode status, mileage, or duration. Compare immediate, delayed, and hysteretic
effects.

### G. Unknown-scenario mechanisms

#### UNK-01 — Element unknowns

Cross unknown target/mode, number of unknown elements, layer topology,
duration model, self-transition policy, catalogue size, rarity composition,
and transition concentration.

#### UNK-02 — Hidden triggering-condition route

Compare `enable_hidden_triggering_unknowns=true/false`. Test one versus many
unknown triggering elements, transitions between different unknown triggering
elements, per-element versus merged-category episode semantics, and triggering
layer duration/count changes.

#### UNK-03 — Full-scenario rarity enablement

Compare enabled/disabled while holding element-unknown routes fixed. Then run
with no element unknowns, each element-unknown layer, and all element-unknown
layers to quantify overlap and exclusion behavior.

#### UNK-04 — Full-scenario target stationary mass

Use the broad probability grid within `(0,1)`, with dense coverage from
`10⁻⁶` to `0.05` and stress values through `0.99`. Increase calibration sample
count as required by the target. Measure threshold stability, episode
fragmentation, occupancy, and overlap.

#### UNK-05 — Full-scenario calibration samples

Use the standard sample-count grid, the validator's exact minimum, points just
below/above it, and sample counts targeting 5%, 2%, 1%, 0.5%, and 0.1%
relative calibration error. Validate out of sample with an independent,
substantially larger calibration set.

#### UNK-06 — Full-scenario calibration seed

Use 100–1,000 seeds at each shortlisted target/sample-size pair. Separate
threshold uncertainty from driving-history uncertainty.

#### UNK-07 — Pattern combinations enablement

Compare `enable_unknown_combinations=false/true`; no manual rules, one rule,
all manual rules, generated-only rules, and mixed manual/generated rules.

#### UNK-08 — Manual pattern-rule design

Test every valid pair of layers, 3–6-layer rules, common/common through
very-rare/very-rare combinations, overlapping rules, nested rules, duplicate
semantic conditions, and rule masses spanning orders of magnitude.

#### UNK-09 — Generated pattern rules

Vary:

- `generated_max_rules`: `0, 1, 2, 5, 10, 25, 50, 100, 500, 1,000`;
- `generated_layers_per_rule`: every integer from 2 through 6;
- `generated_target_mass`: the broad probability grid;
- `seeds.pattern_rules`: at least 100 seeds.

Measure achieved mass, duplicate rejection, rule-count saturation, coverage,
episode counts, and construction/runtime cost.

#### UNK-10 — Hash-combination mechanism

Cross `enable_unknown_combinations`, `enable_hash_combinations`,
`unknown_combination_probability`, and `global_seed`. Use the broad probability
grid, including zero and near one. Test ID/name stability, hash uniformity,
seed stability, and computational cost.

#### UNK-11 — Unknown-route interaction matrix

Run every valid on/off combination of:

- visible element unknowns;
- hidden triggering route;
- manual patterns;
- generated patterns;
- hash combinations;
- full-scenario rarity.

For enabled combinations, cross low/medium/high target masses. Report raw sums,
union time, pairwise overlap, triple overlap, precedence/exclusion, and episode
fragmentation. Include invalid combinations such as conditional transitions
plus the current independent full-scenario classifier as validation cases.

#### UNK-12 — Unknown episode semantics

If episode semantics become configurable, compare restart versus continuation
when moving between unknown elements, merged versus per-layer episodes,
priority versus concurrent routes, self-transition continuation, end-of-run
truncation, and zero-duration boundary transitions.

### H. Interactions that must be studied explicitly

One-factor-at-a-time studies are insufficient for these relationships.

#### INT-01 — Exposure core

`unknown probability × unknown duration mean × duration CV × speed × self-transition policy`

This determines frequency, persistence, exposure time, and distance occupied.

#### INT-02 — Taxonomy and calibration

`catalogue size × unknown-element count × rarity proportions × base-weight ratios × unknown-weight mode × concentration`

This determines whether the designed unknown mass is feasible and stable.

#### INT-03 — Duration tail and clamp

`distribution family × mean × CV × minimum-duration clamp`

This determines moment bias, long episodes, and runtime.

#### INT-04 — Conditional risk concentration

`context prevalence × selector breadth × multiplier strength × target layer × unknown target`

This determines whether risk is globally diffuse or concentrated in specific
contexts.

#### INT-05 — Unknown-route overlap

`element target mass × full-scenario target mass × pattern mass × hash probability × hidden-trigger mode`

This determines total union exposure and double-counting behavior.

#### INT-06 — Full-scenario calibration

`target stationary mass × calibration samples × calibration seed × catalogue size × concentration`

This determines threshold precision and initialization cost.

#### INT-07 — Observation design

`total mileage × window size × number of seeds × event rarity × duration tail`

This determines whether estimates are stable enough to support conclusions.

#### INT-08 — Computational scaling

`mileage × mean duration × catalogue size × conditional-rule count × pattern-rule count × calibration samples × enabled mechanisms`

This identifies time and memory bottlenecks.

#### INT-09 — Layer time-scale ratios

Vary all pairwise ratios of mean layer durations. Test synchronous, nearly
synchronous, and orders-of-magnitude-separated layers to expose tie handling,
tuple persistence, and clustering.

#### INT-10 — Global sensitivity design

After screening, place all influential numeric parameters into Morris and
Sobol/global variance-decomposition experiments. Use Latin hypercube or
quasi-random sampling over valid transformed ranges. Include discrete model
choices using stratified designs or separate structural models. Report first-
order and total-order effects plus interaction rankings.

### I. Validation, boundary, and robustness studies

#### VAL-01 — Numeric boundaries

Test zero, negative, non-finite, extremely small, extremely large, integer
overflow, and floating-point-near-boundary values for every numeric field.
Confirm either a clear validation error or stable defined behavior.

#### VAL-02 — Probability normalization

Test sums equal to one, within tolerance, just outside tolerance, highly
imbalanced vectors, subnormal probabilities, and normalization under extreme
multipliers.

#### VAL-03 — Catalogue validation

Test missing/extra fields, empty catalogues, duplicate IDs, invalid IDs,
empty labels/descriptions, invalid rarities, unknown-element mismatch with
`allow_unknown`, infeasible unknown weights, and unsupported construction-form
combinations.

#### VAL-04 — Conditional-rule validation

Test missing keys, duplicate IDs, unknown layers/elements/rarities, self
dependency, cycles, empty selectors, duplicates, negative/NaN/infinite
multipliers, all-zero adjusted distributions, and deep valid DAGs.

#### VAL-05 — Combination-rule validation

Test fewer than two layers, unknown layers/elements, duplicate rules,
impossible matches, generated mass unattainability, and maximum-rule limits.

#### VAL-06 — Simultaneous event and floating-point ties

Create deterministic and near-deterministic durations that cause exact or
near simultaneous expiries. Test dependency ordering, episode opening/closing,
union-time accounting, and checkpoint equivalence.

#### VAL-07 — End-boundary behavior

Place transitions and episode starts/ends exactly at target mileage, window
boundaries, time zero, and checkpoint boundaries. Verify truncation and window
assignment conventions.

#### VAL-08 — Invariance and metamorphic tests

Verify expected invariances under common weight scaling, non-behavioral label
changes, output/logging changes, equivalent probability parameterizations,
and time/mileage unit conversions. Verify expected non-invariances when IDs
feed hash classification or rules.

### J. Performance and scalability studies

#### PERF-01 — Event-loop scaling

Measure complexity versus mileage, speed, mean duration, number of layers, and
events. Confirm near-linear scaling in event count.

#### PERF-02 — Catalogue scaling

Measure initialization and transition-sampling performance at 1–100,000
elements per layer if supported. Include dense and sparse probability vectors.

#### PERF-03 — Conditional-rule scaling

Measure cost by rule count, selector breadth, simultaneously matched rules,
and dependency depth. Identify compilation versus per-transition cost.

#### PERF-04 — Unknown-classifier scaling

Measure pattern, hash, and full-scenario classification separately and in
combination. Vary rule count, tuple size, target mass, and calibration samples.

#### PERF-05 — Episode density and memory

Increase unknown probabilities and episode fragmentation until memory or output
becomes limiting. Measure list growth, union-merging cost, CSV/JSON size, and
plotting limits.

#### PERF-06 — Checkpoint strategy

Vary wall limit, checkpoint frequency, checkpoint size, compression, and
resume count. Measure overhead and verify bit identity.

#### PERF-07 — Parallel replication

Benchmark serial versus process-level parallel studies, including CPU, memory,
I/O contention, deterministic seed allocation, and result merge correctness.

### K. Model-fidelity and external-validation studies

#### FID-01 — Analytical versus simulated expectations

For every configuration where closed forms are available, compare stationary
mass, transition rate, expected episodes, duration moments, and dispersion.
Map approximation error across rare-event probability, self-transition, and
duration CV.

#### FID-02 — Empirical-data calibration

Fit route probabilities, element frequencies, transition dependencies, and
duration distributions to real or labelled scenario data. Compare alternative
fitting methods, held-out likelihood, calibration plots, and predictive
coverage.

#### FID-03 — Catalogue expert uncertainty

Gather several expert rarity assignments and probability estimates. Treat
expert identity as a model configuration and quantify between-expert outcome
variation.

#### FID-04 — Temporal and geographic transfer

If datasets exist, calibrate by road type, country, season, weather regime,
day/night, traffic density, and operational design domain. Test transfer to
held-out domains.

#### FID-05 — Alternative risk definitions

Compare occupancy-based unknown exposure, entry-based episodes, unique tuple
counts, severity-weighted exposure, context-conditioned exposure, and
time-to-first-unknown. Determine which conclusions depend on the chosen risk
metric.

## 5. Recommended execution program after the redesign

### Phase 0 — Correctness and freeze

Run all `VAL` and `RNG-04` studies. Do not begin sensitivity work until these
pass.

### Phase 1 — Cheap construction screening

Run catalogue, rarity, weight, concentration, and calibration studies that do
not require long driving histories. Use hundreds or thousands of construction
seeds.

### Phase 2 — One-factor wide screening

Run the complete wide grids for `RUN`, `DUR`, `CAT`, `TRN`, `COND`, and `UNK`
with at least five runtime seeds. Use a benchmarked screening mileage that is
long enough for directionally reliable results.

### Phase 3 — Global sensitivity

Use Morris screening across all valid numeric parameters, then Sobol or another
variance-decomposition method on the influential subset. Treat structural
switches as stratified model families.

### Phase 4 — Interaction studies

Run every `INT` design, prioritizing exposure core, taxonomy/calibration,
unknown-route overlap, and observation design.

### Phase 5 — Confirmation and tails

Confirm shortlisted configurations at the full final mileage with at least 20
seeds. Use 50–200 seeds or sequential precision targets for p99.9, maxima, and
threshold-exceedance probabilities.

### Phase 6 — Performance and external validation

Run scalability studies and compare the final model families with analytical
predictions and empirical data.

## 6. Current configuration coverage matrix

This matrix ensures that every field currently accepted by `SimConfig` or its
nested rule/catalogue structures has a planned study.

| Current field or structure | Covered by |
|---|---|
| `seeds.element_count` | RNG-01, RNG-02, CAT-02 |
| `seeds.rarity_assignment` | RNG-01, RNG-02, CAT-04 |
| `seeds.transition_matrix` | RNG-01, RNG-02, TRN-06 |
| `seeds.duration` | RNG-01, RNG-02, DUR-01–08 |
| `seeds.initial_state` | RNG-01, RNG-02, TRN-08 |
| `seeds.transition_sampling` | RNG-01, RNG-02 |
| `seeds.pattern_rules` | RNG-01, UNK-09 |
| `global_seed` | RNG-01, UNK-10 |
| `target_total_miles` | RUN-01, INT-07 |
| `average_speed_mph` | RUN-02, RUN-05, INT-01 |
| `min_duration_seconds` | RUN-03, DUR-03, INT-03 |
| `mileage_window_miles` | RUN-04, INT-07 |
| `transition_model.mode` | COND-01 |
| `transition_model.conditional.apply_to_initial_state` | COND-02 |
| conditional rule `id` | COND-06–07, VAL-04 |
| conditional rule `target_layer` | COND-05–06 |
| conditional `when` parent layers | COND-04–06 |
| conditional selector `elements` | COND-04–05 |
| conditional selector `rarities` | COND-04–05 |
| multiplier `elements` | COND-03, COND-05, COND-07 |
| multiplier `rarities` | COND-03, COND-05, COND-08 |
| `enable_unknown_combinations` | UNK-07, UNK-11 |
| `enable_hash_combinations` | UNK-10, UNK-11 |
| `enable_hidden_triggering_unknowns` | UNK-02, UNK-11 |
| `combination_rules.manual` | UNK-08 |
| `generated_max_rules` | UNK-09, PERF-04 |
| `generated_layers_per_rule` | UNK-09 |
| `generated_target_mass` | UNK-09, UNK-11 |
| `unknown_combination_probability` | UNK-10, UNK-11 |
| `full_scenario_unknowns.enabled` | UNK-03, UNK-11 |
| `target_stationary_mass` | UNK-04, INT-05–06 |
| `calibration_samples` | UNK-05, INT-06, PERF-04 |
| `calibration_seed` | RNG-01, UNK-06, INT-06 |
| `rarity_proportions.common` | TRN-01 |
| `rarity_proportions.medium` | TRN-01 |
| `rarity_proportions.rare` | TRN-01 |
| `rarity_proportions.very_rare` | TRN-01 |
| `rarity_proportions.unknown` | TRN-01, CAT-05, UNK-01 |
| `base_weights.common` | TRN-02 |
| `base_weights.medium` | TRN-02 |
| `base_weights.rare` | TRN-02 |
| `base_weights.very_rare` | TRN-02 |
| `unknown_weight_mode` | TRN-03 |
| `target_unknown_element_probability` | TRN-04, INT-01–02 |
| `fixed_unknown_weight` | TRN-05 |
| `concentration_scale` | TRN-06, INT-02, INT-06 |
| `allow_self_transition` | TRN-07, INT-01 |
| layer `mean_duration` | DUR-01, DUR-03, INT-09 |
| layer `variance_duration` | DUR-02–03 |
| layer `allow_unknown` | CAT-06, UNK-01 |
| `fixed_elements[].name` | CAT-07–09, UNK-10 |
| `fixed_elements[].probability` | CAT-09 |
| `element_count_min` | CAT-01–02, INT-02 |
| `element_count_max` | CAT-01–02, INT-02 |
| `semantic_catalog.version` | CAT-07 |
| semantic element `id` | CAT-03, CAT-07–08, COND-05, UNK-10 |
| semantic element `label` | CAT-07 |
| semantic element `description` | CAT-07 |
| semantic element `rarity` | CAT-04–05, TRN-01–02 |
| checkpoint wall limit and checkpoint path | RNG-04, PERF-06 |
| plot/no-plot and output path behavior | RNG-04, PERF-05 |

## 7. Required artefacts for each completed study

Every future study folder should contain:

- `README.md` or `report.md` with the question, design, outcome, limitations,
  and recommendation;
- the executable study runner;
- an immutable baseline configuration snapshot;
- one complete configuration or configuration hash for every run;
- `runs.csv` with one row per run;
- aggregate tables with means, uncertainty, minima, and maxima;
- machine-readable JSON with the full design and results;
- plots showing individual runs as well as aggregates;
- validation logs, simulator version/commit, dependency versions, and wall time;
- a declaration of which parameters were held fixed;
- a declaration of invalid configurations and why they were rejected;
- a rerun command and deterministic seed-allocation rule.

No study should conclude that a parameter “has no effect” merely because the
mean changed little. Tail behavior, clustering, overlap, calibration,
uncertainty, and computational cost must also be checked.
