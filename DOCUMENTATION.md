# Technical Documentation — Generated-Element Simulator (v6)

## 1. Model overview

The simulator has six layers in a fixed order:

1. `street`
2. `temporal_modifications`
3. `ego_maneuver`
4. `ru_maneuver`
5. `environmental_conditions`
6. `triggering_conditions`

Every layer is generated from `element_count_min` and
`element_count_max`. There is no semantic-catalogue or fixed-element
construction path.

## 2. User-configured class percentages

Two independent mappings are required.

### 2.1 Element-class percentages

`element_class_percentages` controls the percentage of generated elements in
each class. For a layer containing \(N\) elements, the ideal count is:

\[
e_r = N \frac{E_r}{100}
\]

where \(E_r\) is the configured percentage for rarity \(r\).

The simulator floors every \(e_r\), then assigns the remaining elements to
the classes with the largest fractional remainders. This guarantees integer
counts whose sum is exactly \(N\).

Configuration validation checks every possible count in every layer range.
Each count must produce at least one common, rare, and unknown element.

### 2.2 Selection-class percentages

`selection_class_percentages` directly controls the total probability mass
of each rarity class. Let:

\[
P_r = \frac{S_r}{100}
\]

where \(S_r\) is the configured selection percentage. If class \(r\)
contains \(n_r\) elements, its initial per-element probability is:

\[
p_i = \frac{P_r}{n_r}
\]

The initial probability vector therefore has exact class totals:

\[
\sum_{i \in r} p_i = P_r
\]

To create different probabilities for elements, the simulator first draws one
raw Dirichlet vector:

\[
z \sim \operatorname{Dirichlet}(c p)
\]

where \(c\) is `concentration_scale`.

When `rescale_transition_class_masses` is `true` (the default), it then
rescales each class:

\[
q_i =
P_r
\frac{z_i}{\sum_{j \in r} z_j}
\]

Consequently:

\[
\sum_{i \in r} q_i = P_r
\]

In this mode, the Dirichlet draw changes only the distribution between elements
inside the same class. It cannot change the configured class percentages.

When `rescale_transition_class_masses` is `false`, the transition vector is
instead kept directly as:

\[
q_i = z_i
\]

The complete vector still sums to one, but the realized class mass is:

\[
\sum_{i \in r} q_i = \sum_{i \in r} z_i
\]

and therefore varies reproducibly around \(P_r\). The initial-state vector is
not affected by this switch and always retains the exact configured class
totals.

There are no rarity weights, no unknown-weight mode, and no analytical
unknown-weight equation.

## 3. Configuration validation

Both percentage mappings must:

- be mappings;
- contain exactly `common`, `rare`, and `unknown`;
- use positive finite numeric percentages;
- sum to 100 within floating-point tolerance.

Every layer must have positive durations and a valid inclusive generated
element-count range.

## 4. Per-element durations

Every element receives a Gamma distribution. For rarity \(r\), layer baseline
\(\mu_L\), stable within-class position \(u_i \in [-1,1]\), rarity mean
multiplier \(m_r\), and spread \(s_r\):

\[
\mu_i = \mu_L m_r(1+s_r u_i)
\]

With rarity coefficient of variation \(CV_r\):

\[
\sigma_i^2=(\mu_i CV_r)^2
\]

The Gamma parameters are:

\[
\operatorname{shape}_i=\frac{\mu_i^2}{\sigma_i^2},
\qquad
\operatorname{scale}_i=\frac{\sigma_i^2}{\mu_i}
\]

Sampled durations below `min_duration_seconds` are clamped to that minimum.

## 5. Unknown-scenario combinations

At construction, the simulator enumerates eligible combinations of rare
elements from distinct layers. Each eligible rule includes a rare element from
`triggering_conditions`.

This exact C3-C6 rule system is the only unknown-scenario mechanism in the
runtime. The earlier standalone-element, hidden-triggering, hash/pattern, and
full-scenario probability mechanisms and their configuration fields have been
removed.

The configured numbers of C3, C4, C5, and C6 rules are selected reproducibly.
A rule matches only when:

- every selected rare element is active;
- no additional rare element is active;
- no unknown element is active;
- every remaining layer is common.

Unknown-rarity elements are ordinary generated selection/duration classes.
They do not independently open unknown-scenario episodes.

## 6. Event loop

The simulator samples an initial element and duration for every layer. It then
jumps directly to the next layer expiry, advances simulated time and derived
mileage, samples replacement elements for expired layers, and draws new
element-specific durations.

The loop stops exactly at `target_total_hours`. Checkpoint and resume preserve
all random states and are bit-identical to an uninterrupted run.

## 7. Results

`stats.json` stores `element_rarity_composition` with:

- `configured_element_class_percentages`;
- `configured_selection_class_percentages`;
- per-layer counts and achieved element proportions;
- aggregate counts and proportions across all layers.

Each layer also reports `transition_class_proportions`, allowing direct
verification that its permanent common/rare/unknown masses equal the requested
selection percentages.

`summary.md` renders the element composition as a table and reports the direct
selection percentages in the run parameters and per-layer diagnostics.

The duration-distribution folder contains one theoretical Gamma PDF/CDF
comparison per layer and a JSON manifest of the plotted element parameters.

## 8. Reproducibility

Independent seeds control element counts, rarity assignment, the within-class
Dirichlet variation, durations, initial states, transition sampling, and rule
selection. The same configuration and seeds produce the same result.
