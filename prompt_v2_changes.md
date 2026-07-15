# Change Request v2 — Layered Scenario Model Simulator

The simulator is built and working according to the original specification
(per-tuple unknown-encounter counting, 6 layers, rarity-weighted Dirichlet
transitions, Gamma durations, SHA-256 unknown combinations, event-driven
2,000,000-mile run). This change request modifies the unknown-scenario
counting semantics, makes element counts realistic, and adds two
investigations. Implement all items below.

---

## 1. Replace per-tuple counting with unknown-episode durations

Remove the current per-tuple encounter counting entirely. Instead, measure
**unknown-element episodes**: how long the system stays in an unknown
scenario, counted once per cause.

**Motivation.** Today, if the environment layer holds an unknown element
and the ego layer then changes its element, a new scenario tuple is formed
and a second encounter is counted. Under the new semantics this must be
ONE unknown episode with a measured duration, not two counts.

**Episode rules (normative):**

1. An episode **starts** when a layer transitions from a known element to
   an unknown element. It also starts at t = 0 for any layer whose initial
   element is unknown.
2. An episode **ends** when that same layer transitions from that unknown
   element to a **known** element.
3. If a layer transitions directly from one unknown element to a
   **different** unknown element, the first episode ends at the hop and a
   **new episode starts** at the same instant (two episodes, two
   durations).
4. A self-transition back onto the **same** unknown element does not end
   the episode; the episode continues.
5. Episodes are tracked **per layer** and may overlap in time: if layer A
   is in an unknown element and layer B then enters an unknown element,
   that is a **second, separate episode** with its own duration. Each
   episode ends independently, when its own layer leaves its unknown
   element (rule 2/3).
6. Changes in *other* layers while an episode is running never create new
   episodes and never end running ones.
7. An episode still open when the simulation reaches the target mileage is
   closed at the final simulation time and flagged `truncated = true`.

**Recorded per episode:** episode index, layer, unknown element name,
start time (s), end time (s), start mileage, end mileage, duration in
seconds, duration in miles, truncated flag.

**Outputs (replace the old encounter outputs):**

- `episodes.csv` with the fields above.
- Total number of unknown episodes and episodes per 1,000,000 miles.
- Episode duration statistics (mean, median, p90, max — in seconds and in
  miles).
- Inter-arrival distances and times between episode **starts** (first
  entry measured from the start of the simulation).
- Count of episode starts per fixed mileage window, with empirical mean,
  empirical variance, and dispersion index = variance / mean (window size
  stays `mileage_window_miles`).
- Total time spent in an unknown scenario as the **union** of episode
  intervals (overlaps counted once), reported in seconds and as a
  percentage of total simulated time.
- Updated plots: cumulative episodes vs mileage, episode-duration
  histogram, inter-arrival histogram, per-window counts, per-layer
  episode counts.

**Update the unit tests** to pin the new semantics, at minimum: the
overlap example above yields exactly 2 episodes with independent end
times; unknown→unknown hop in one layer yields 2 episodes (rule 3);
other-layer changes during an episode add nothing (rule 6); truncation at
simulation end (rule 7); reproducibility of the full episode list from
the same config and seeds, including across checkpoint/resume.

---

## 2. Disable unknown combinations (temporary)

Disable the hash-based unknown-combination mechanism for now: only
transitions into unknown **elements** create unknown episodes.

- Add a config switch (e.g. `enable_unknown_combinations: false`, default
  false) rather than deleting the mechanism.
- Keep `UnknownCombinationClassifier`, its `global_seed` semantics, and
  its unit tests intact and passing — the mechanism will be reimplemented
  at a later stage within the episode framework.
- Leave a clearly visible note in `config.yaml`, `README.md`, and
  `DOCUMENTATION.md`: unknown combinations are temporarily disabled; when
  reintroduced, an open design question is how a combination-unknown maps
  to an episode (a candidate definition: the lifetime of that exact tuple).

---

## 3. Realistic element counts per layer (research task)

The current uniform range of 50–100 elements per layer for all six layers
is a placeholder. Research what a reasonable number of elements is for
each layer.

- Search the literature on layered scenario models and ODD taxonomies —
  e.g. the PEGASUS / 6-layer scenario model publications and
  ODD-taxonomy standards (ISO 34503, BSI PAS 1883, ASAM OpenODD) — for
  defensible element counts per layer: street types, temporal
  modifications, ego/RU maneuver classes, environmental conditions,
  triggering conditions.
- Convert the findings into **per-layer `[min, max]` ranges** in the
  config (replacing the single global `element_count_min/max`). Element
  counts are still sampled uniformly from the layer's range, and the
  rarity-assignment mechanism (largest-remainder + shuffle) is unchanged.
- **Cite the sources** for every proposed range in the documentation.
- **If no defensible number can be found for a layer, say so explicitly
  and do not assume one.** Keep that layer's current range and flag it as
  an open question instead of inventing a value.
- Mind the interaction with `unknown_weight_mode = "calculated"`: each
  layer that allows unknown elements still needs at least one unknown
  element after the proportions are applied to the (possibly much
  smaller) element count. Validate and report if a proposed range would
  violate this.
- Exceptions: do **not** change the triggering-conditions layer (see §5),
  and the street layer is excluded from this research because it now has
  a fixed element list (see §6). Research scope:
  temporal_modifications, ego_maneuver, ru_maneuver,
  environmental_conditions.

---

## 4. Investigate the Dirichlet concentration value

Determine what `concentration_scale` should be used, as a short study
(markdown report + plots), ending in a recommended default:

- **Analytical part:** with `alpha = c · normalized_weights`, a layer's
  realized unknown probability mass follows Beta(c·p, c·(1−p)) with
  p ≈ 0.004; derive how its standard deviation / coefficient of variation
  shrinks with c, and explain the observed per-layer scatter at c = 100
  (realized rates between ~0.003 % and ~0.5 % in the delivered run).
- **Experimental part:** sweep several values (e.g. c ∈ {100, 1,000,
  10,000, 100,000}) across many `transition_matrix` seeds (e.g. ≥ 20 per
  value); quantify the spread of realized per-layer unknown mass around
  the 0.4 % target (and optionally of the empirical selection rate in
  short simulation runs).
- **Recommendation:** propose a value based on an explicit criterion —
  for example, the smallest c for which ~95 % of layers land within
  ±25 % of the 0.4 % target — set it as the new default in
  `config.yaml`, and document the trade-off (higher c = faithful to the
  designed weights, lower c = more random transition behavior).

---

## 5. Triggering-conditions layer — note only, no change

Leave the triggering-conditions layer exactly as it is (element-count
range and all other parameters). Add a visible TODO note in
`config.yaml`, `README.md`, and `DOCUMENTATION.md`:

> Future investigation: vary the number of elements in the
> triggering-conditions layer and quantify the effect on unknown-episode
> statistics (episode count, durations, dispersion). To be done at a
> later stage; not part of this change.

---

## 6. Street layer: fixed real elements with exact transition probabilities

Replace the synthetic street elements with the following 12 real
route-composition elements. Their shares are used **exactly as given** as
the street layer's permanent transition probability vector — **no
Dirichlet draw for this layer** — and the initial street element is
sampled from the same vector. The shares sum to exactly 1.0.

| element | probability |
|---|---|
| constant_lane | 0.493 |
| forced_merge_proceeding | 0.169 |
| road_split_proceeding | 0.079 |
| lane_split_proceeding | 0.072 |
| added_lane_proceeding | 0.034 |
| road_split_exiting | 0.014 |
| lane_split_exiting | 0.013 |
| removed_lane | 0.012 |
| forced_merge_merging | 0.010 |
| added_lane_merging | 0.006 |
| added_lane | 0.003 |
| overlap_zone | 0.095 |

- The street layer therefore has exactly 12 elements, all **known** (no
  unknown elements — see §7); it can never start an unknown episode.
- Rarity categories are irrelevant for this layer's dynamics (weights are
  not used); any rarity labels kept for reporting are cosmetic only.
- Street element durations keep the layer's Gamma parameters
  (`mean_duration`, `variance_duration`) — one duration model for the
  layer, as before.
- The fixed list and probabilities live in `config.yaml` (validated: sum
  to 1 within tolerance, all positive, unique names).
- Self-transitions: sampling may return the current element with its
  listed probability (e.g. `constant_lane` 49.3 %), subject to the global
  `allow_self_transition` setting, as for the other layers.

## 7. Remove unknown elements from the street and weather layers

Neither the street layer nor the weather layer
(`environmental_conditions`) may contain unknown elements:

- **street:** guaranteed by construction (§6 fixed list, all known).
- **environmental_conditions:** add a per-layer switch (e.g.
  `allow_unknown: false`). Its rarity proportions are the four known
  categories renormalized to sum to 1 (0.50/0.25/0.10/0.05 → ≈
  0.5556/0.2778/0.1111/0.0556); the unknown-weight calculation is skipped
  for layers without unknown elements.
- Consequence (intended): unknown episodes can only originate in
  temporal_modifications, ego_maneuver, ru_maneuver, and
  triggering_conditions.

---

## General constraints

- Everything new must be configurable via `config.yaml`; no hardcoded
  values.
- Reproducibility is preserved: the existing per-source seeds
  (`element_count`, `rarity_assignment`, `transition_matrix`, `duration`,
  `initial_state`, `transition_sampling`) and `global_seed` keep their
  roles; the same config must produce identical results, including across
  checkpoint/resume.
- The event-driven engine, Gamma-duration model, rarity weighting,
  unknown-weight modes, and the once-only Dirichlet transition vectors
  are unchanged except where §1–§2 require it.
- Update `test_simulator.py`, `README.md`, and `DOCUMENTATION.md` to
  match the new semantics; all tests must pass.
- Rerun the full 2,000,000-mile simulation and regenerate
  `results/` (CSV, summary, stats, plots) under the new counting.

**Acceptance example (must hold):** layer A enters an unknown element at
t₁; layer B enters an unknown element at t₂ > t₁ while A is still
unknown; A returns to a known element at t₃; B returns to a known element
at t₄. Result: exactly two episodes — (A: t₁→t₃) and (B: t₂→t₄) — and any
number of other-layer element changes in between adds no further counts.

---

## 8. (v3 addendum) Reintroduce unknown combinations: hash + patterns

Supersedes the "temporarily disabled" state of §2. Keep the SHA-256 hash
method AND add pattern-based combinations; both are episodic and coexist
with element episodes:

- **Hash combinations:** evaluated when the scenario tuple changes and
  all six elements are known (original gating). Episode = lifetime of
  that exact tuple: any element change ends it, self-transitions continue
  it. Threshold `unknown_combination_probability`, seed `global_seed`.
- **Pattern combinations:** configured rules = conjunctions of specific
  KNOWN-rarity elements in ≥2 layers (wildcards elsewhere); a rule's
  episode runs while all its elements are simultaneously current. Rules
  are manual (`combination_rules.manual`) and/or generated once from a
  new `seeds.pattern_rules` stream, accumulating random
  `generated_layers_per_rule`-layer rules until
  `generated_target_mass` (≈0.5%) total stationary mass is reached
  (capped at `generated_max_rules`). Rule mass = product of its elements'
  stationary probabilities; the analytical model must predict pattern
  episodes via E[episodes] = T·mass·hazard, E[duration] = 1/hazard.
- Episodes of all three types are separate counts with independent
  durations; the union unknown time merges overlaps of any mix of types.
- `enable_unknown_combinations: false` disables both mechanisms.

Status: IMPLEMENTED (v3) — 38 tests, 2M-mile run regenerated, analytical
model extended, docs updated.
