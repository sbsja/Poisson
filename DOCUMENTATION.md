# Technical Documentation — Layered Scenario Model Simulator (v2)

This document explains exactly how every part of the program works,
component by component, in the order data flows through the system.
File references: `simulator.py` (core), `run_simulation.py` (runner),
`config.yaml` (parameters), `test_simulator.py` (tests). Version 2
implements the change request in `prompt_v2_changes.md`: unknown-EPISODE
duration measurement (replacing per-tuple encounter counting), a fixed
real-element street layer, no unknown elements in street/weather,
research-based element counts, and a studied Dirichlet concentration.

> **Current configuration override:** Both pattern and hash combinations are
> disabled in `config.yaml`. The active simulation builds no combination
> rules, does not instantiate the hash classifier, and emits only
> element-level unknown episodes. Later combination sections describe optional
> mechanisms retained in the code, not behavior of the delivered configuration.

---

## 1. Big picture

```
config.yaml
    │  SimConfig.from_yaml()  →  validation (incl. per-n feasibility)
    ▼
ScenarioSimulator.__init__()
    │  6 independent RNG streams (one per random source)
    │  build_layer() ×6:
    │     street: fixed 12 elements, exact vector (no Dirichlet, no RNG)
    │     others: element count → rarity counts → shuffle → unknown weight
    │             → weight vector → ONE Dirichlet draw → cumulative arrays
    ▼
run() / run_resumable()
    │  _new_state(): initial element + duration per layer; episodes open
    │                at t=0 for layers starting on an unknown element
    │  event-driven loop until target mileage:
    │     jump to next expiry → advance time & miles → transition expired
    │     layers → episode rules 1–4 per transitioned layer
    │  at target: close open episodes (truncated=true)
    ▼
SimulationResult
    │  episodes (layer, element, start/end time & mileage, duration,
    │  truncated), union unknown time, per-layer statistics
    ▼
run_simulation.py → episodes.csv, windows.csv, summary.md, stats.json,
                    plots/*.png
```

Layer order (constant `LAYER_DEFINITIONS`): street, temporal_modifications,
ego_maneuver, ru_maneuver, environmental_conditions, triggering_conditions.
Layers are fully independent — no conditional probabilities between layers,
one transition vector per layer.

---

## 2. Configuration (`SimConfig`, `LayerParams`)

`SimConfig.from_yaml → from_dict` builds the dataclass, converts each
`layers:` entry into a `LayerParams` (durations + either
`element_count_min/max` + `allow_unknown`, or `fixed_elements`), rejects
unknown keys, then runs `validate()`.

Validation highlights: the `seeds` mapping must contain exactly the six
required integer entries; `enable_unknown_combinations: true` is rejected
with an explanatory error (mechanism temporarily disabled, see §7);
rarity proportions must cover all five categories and sum to 1; base
weights positive, `base_weights['unknown']` forbidden; per layer —
durations positive, and either a valid fixed-element list (unique names,
positive probabilities summing to 1, `allow_unknown: false`) or a valid
count range. For every sampled layer that allows unknowns, **every n in
[min, max] is checked**: it must yield ≥1 unknown element by
largest-remainder rounding AND admit a valid unknown weight (< very_rare
weight) under the configured mode. This is what caught the ego/RU n=13–14
infeasibility documented in `research_element_counts.md`.

`effective_proportions(lp)`: layers with `allow_unknown: false`
(environmental_conditions) use the four known proportions renormalized to
sum to 1 (0.50/0.25/0.10/0.05 → ≈0.5556/0.2778/0.1111/0.0556), unknown
share 0.

---

## 3. Random-number streams (reproducibility)

One dedicated RNG per random source, seeded from `config.seeds`:

| seed key | controls |
|---|---|
| `element_count` | number of elements per sampled layer (uniform in the layer's range) |
| `rarity_assignment` | shuffling rarity categories across elements |
| `transition_matrix` | the Dirichlet draws of the transition vectors |
| `duration` | every Gamma duration (initial + during simulation) |
| `initial_state` | the initial element of each layer |
| `transition_sampling` | next-element selection during simulation |

`global_seed` belongs solely to the (dormant) hash classifier. The street
layer consumes **no randomness at construction** — its vector is the
configured probabilities verbatim — so changing `transition_matrix` or
`element_count` seeds provably leaves it untouched
(`test_street_vector_not_dirichlet_perturbed`,
`test_seed_streams_isolated`). Same config ⇒ identical results, including
across checkpoint/resume (`test_chunked_resume_bit_identical`).

---

## 4. Layer construction (`build_layer`)

**Fixed layer (street).** The 12 route-composition elements from the
config are taken as-is: their probabilities (validated to sum to 1) form
both the permanent transition vector and the initial-state distribution —
**no Dirichlet perturbation**. All elements are known; `unknown_weight`
is None. Rarity labels are assigned by probability band (≥10% common,
≥3% medium, ≥1% rare, else very_rare) for reporting only — they have no
effect on dynamics. Durations use the layer's Gamma parameters like any
other layer.

**Sampled layers.** As in v1: element count uniform in the layer's
configured range; largest-remainder integer rarity counts from the
effective proportions; random shuffle; names `prefix_iii`; rarity-based
weights with the unknown weight from §5 (only if the layer has unknown
elements); normalization; one permanent Dirichlet draw with
`alpha = concentration_scale · normalized_weights`; cumulative arrays for
O(log n) categorical sampling.

`concentration_scale = 20000` is not arbitrary: `concentration_study.md`
derives analytically that a layer's realized unknown mass is
Beta(c·p, c·(1−p)) with std √(p(1−p)/(c+1)), and a Monte Carlo sweep shows
c=20000 is the smallest tested value putting ≥95% of draws within ±25% of
the 0.4% target (c=100: ~10%).

---

## 5. Unknown-element weight (`compute_unknown_weight`)

Unchanged from v1 — `"calculated"` mode solves
`w = p·known_mass / (n_u·(1−p))` so the layer's designed unknown mass is
exactly `target_unknown_element_probability` (0.004); `"fixed"` mode uses
`fixed_unknown_weight`. In both modes `w` must be strictly smaller than
the very_rare weight, otherwise a `ConfigError` lists the three remedies
(raise unknown proportion / lower target / use fixed mode). New in v2:
the check runs at config validation for every possible element count, so
infeasible ranges fail fast — e.g. ego/RU layers of 13–14 elements would
need w = 0.0335–0.0351 > 0.03 and are therefore excluded from the default
config (range clipped to [7, 12]).

---

## 6. Durations

Unchanged: every layer draws Gamma durations with
`shape = mean²/var`, `scale = var/mean` (moment matching, unit-tested),
clamped from below to `min_duration_seconds`. All durations in seconds.

---

## 7. Unknown combinations — re-enabled in v3, two mechanisms

**Hash combinations.** `UnknownCombinationClassifier` (SHA-256 over
`"<global_seed>|name1|...|name6"`, normalized by 2²⁵⁶, thresholded by
`unknown_combination_probability`) is active again with its original
semantics: it is evaluated only when the scenario tuple changes AND all
six current elements are known (gated by the `element_unknown_active`
counter). Its episode lasts exactly as long as that specific tuple
persists — any element change in any layer ends it; self-transitions,
which leave the tuple unchanged, continue it. Mean duration ≈ mean tuple
lifetime = 1/Σₖ(1−sₖ)/μₖ ≈ 17 s.

**Pattern combinations** (`CombinationRule`, `build_combination_rules`).
A rule is a conjunction of specific elements in ≥2 layers, e.g.
`street=forced_merge_merging & environmental_conditions=environment_000`;
all other layers are wildcards. A rule is *matched* iff every referenced
element is simultaneously current; the rule's episode runs from the event
where it becomes matched to the event where any referenced layer leaves
its element — so it survives arbitrary churn in unreferenced layers.
Rules come from two sources: `combination_rules.manual` in the config,
and rules generated **once** at initialization from the dedicated
`seeds.pattern_rules` stream (random `generated_layers_per_rule`-layer
conjunctions with uniformly chosen known elements, accumulated until
`generated_target_mass` total stationary mass is reached, capped at
`generated_max_rules`). Validation rejects rules that reference
nonexistent elements, unknown-rarity elements (combinations are
interactions of *known* elements), fewer than two layers, or unknown
layer keys. Each rule's stationary mass is the product of its elements'
transition-vector probabilities — exact, because layers are independent
and transitions i.i.d. — which keeps the analytical model closed-form:
E[episodes] = T·mass·hazard and E[duration] = 1/hazard with
hazard = Σ_{k∈rule}(1−q_k)/μ_k.

Evaluation is incremental: `rules_by_layer` maps each layer to the rules
referencing it, and only rules touching a layer that actually changed in
the current event are re-evaluated — one tuple construction and at most a
handful of comparisons per event.

---

## 8. Episode semantics (the core v2 change)

An **episode** is a contiguous occupancy of one unknown element by one
layer. The normative rules (change request §1):

1. **Start:** a layer transitions known → unknown (also at t=0 if the
   initial element is unknown).
2. **End:** that same layer transitions from that unknown element to a
   known element.
3. **Restart:** a direct hop unknown → *different* unknown closes the
   episode and opens a new one at the same instant.
4. **Continue:** a self-transition onto the *same* unknown element does
   not end the episode.
5. Episodes are per layer and may overlap in time; overlapping episodes
   are separate counts with independent durations.
6. Other layers' changes never start or end an episode.
7. Episodes still open at the end are closed at final time with
   `truncated = true`.

The decision table lives in `episode_transition_action(cur_unknown,
nxt_unknown, same_element)` (unit-tested against all five cases); the hot
loop applies identical logic inline. Bookkeeping per layer: an
`open_episode` slot pointing into the episodes list; opening/closing also
maintains `active_unknown_layers`, from which the **union unknown time**
is accumulated (time intervals where ≥1 episode is active, overlaps
counted once).

Why this replaces per-tuple counting: previously, while a slow layer held
an unknown element, every fast-layer change formed a new unknown *tuple*
and was counted again (hence 141,739 "encounters" and a dispersion index
of ~12 in the v1 run). Under episode counting the same situation is one
episode with a measured duration; with 4 unknown-bearing layers the run
yields 39,227 episodes and a near-Poisson dispersion index of ~0.96.

**Consequence of §6–§7 of the change request:** street (fixed, all known)
and environmental_conditions (`allow_unknown: false`) can never produce
*element* episodes; element episodes originate only in
temporal_modifications, ego_maneuver, ru_maneuver, and
triggering_conditions. All layers can participate in *combination*
episodes (patterns and hash), since those are built from known elements.

**Three episode types coexist** (`Episode.type`): `element`, `pattern`,
`hash_combination`. Each type has its own open-slot bookkeeping (per
layer / per rule / one hash slot), all opened and closed through the same
generic `_open`/`_close` machinery that also maintains the union
unknown-time counter (`episodes_active`), so overlapping episodes of any
mix of types are counted once in the union. Episodes of all types opened
at the same event time are appended in deterministic order (elements by
layer, then patterns by rule index, then hash), preserving bit-exact
reproducibility and checkpoint/resume.

---

## 9. Event-driven main loop (`run_resumable`)

Identical skeleton to v1 — jump by the smallest remaining duration,
advance time and mileage (`delta_miles = mph·dt/3600`), subtract dt from
all layers, transition all expired layers — but per transitioned layer the
episode rules of §8 are applied instead of building scenario tuples. Per
layer the loop also tracks transitions, unknown selections, per-element
visit counts (used to verify the street composition), rarity selections,
and empirical durations. Wall-clock chunking (checkpoint every ~4096
events when `--max-wall-seconds` is set) and pickle-based resume are
unchanged; episode state (open slots, union counters) lives in the state
dict, so resume is bit-identical.

Stop condition: 2,000,000 **miles** (not iterations or seconds); at 50 mph
that is 144,000,000 simulated seconds ≈ 10M events ≈ 16 s wall time.

---

## 10. Output statistics

Per episode (`episodes.csv`): layer, element, start/end mileage, start/end
time, duration in seconds and miles, truncated flag, plus inter-arrival
distance/time from the previous episode start. Derived
(`SimulationResult`): inter-arrivals between episode **starts** (first
entry from t=0), `window_stats()` = episode-start counts per fixed mileage
window (complete windows only; sample variance ddof=1; dispersion index =
variance/mean, ≈1 for a Poisson-like process), episodes per million miles,
union unknown time and its fraction of total time. The runner writes
summary.md / stats.json and six plots (cumulative episodes, duration
histogram, inter-arrival histogram, window counts, per-layer stats, street
composition configured vs simulated).

---

## 11. Test suite (38 tests)

Episode rules decision table; hash classifier determinism/rate/seed
dependence (kept although dormant) and rejection of
`enable_unknown_combinations: true`; largest-remainder counts; unknown
weight formula, target exactness, remedy-listing error, fixed mode,
range-feasibility rejection (n=13–14 case); seeds and fixed-element
validation; street layer exactness (12 elements, vector == configured
probabilities, unaffected by Dirichlet seed); environment layer without
unknowns and renormalized proportions; sampled layers within researched
ranges with valid vectors and exact 0.4% designed mass; permanence of
transition vectors across a run; seed-stream isolation; Gamma moments and
min-clamp; no-self-transition mode; episode behavioral invariants (only
unknown-bearing layers, valid intervals, per-layer non-overlap, ordered
starts, union bounds, duration↔mileage proportionality, truncation
flagging, episodes == unknown entries when self-transitions are disabled,
long episodes surviving other layers' churn); window statistics on known
inputs; inter-arrival consistency; target/time consistency; bit-identical
reproducibility and chunked resume.

Run with `pytest test_simulator.py -q`.


---

## 12. (v4) Full-scenario rarity unknowns

The current simulator uses three mutually distinct routes to an unknown
scenario: normal unknown elements in visible unknown-bearing layers; the
`hidden_triggering_unknown` category for any unknown element in the hidden
`triggering_conditions` layer; and rare full six-layer tuples that contain
known elements only. The latter excludes every tuple covered by either of
the first two routes.

`FullScenarioClassifier` (simulator.py) implements the scenario-level
unknown mechanism that replaces pattern/hash combinations (both disabled
in config):

- **Definition.** For the current complete tuple S, the stationary
  probability is P(S) = q_street(s1)*q_temporal(s2)*...*q_trigger(s6),
  using each layer's realized permanent `transition_probs`. Because layers
  are independent with i.i.d. transitions and duration distributions that
  do not depend on the element, the time-stationary tuple distribution is
  exactly this product measure. S is a full-scenario unknown iff every
  element is known and P(S) <= `calibrated_rarity_threshold`. All six layers
  always enter the classification; there is no hashing and no partial-layer
  matching.
- **Calibration.** At initialization, N = `calibration_samples` tuples are
  drawn from the stationary product distribution itself using a dedicated
  `numpy` RNG seeded with `calibration_seed` (none of the six existing
  streams is consumed, so all other randomness is unchanged). Since the
  samples come from P, the stationary mass of {S : all elements known and
  P(S) <= t} equals the fraction of eligible samples below t; the threshold
  is therefore the k = round(target*N)-th smallest eligible sampled P value.
  The in-sample achieved mass (reported in summary.md/stats.json) matches
  the target up to 1/N; the true mass of the thresholded set carries the
  Monte Carlo quantile error ~ sqrt(target(1-target)/N) (~1.1% relative at
  the defaults). Coverage is measured in probability MASS, never in the
  number of rare tuples.
- **Episode semantics** (type `full_scenario`, layer `scenario`, element =
  pipe-separated tuple): evaluated once per event after all simultaneously
  expired layers are updated, and only when the tuple genuinely changed -
  self-transitions leave both the tuple and any open episode untouched.
  Known -> rare opens; rare -> known closes; rare A -> rare B closes A and
  opens B at the same timestamp; t=0 opens an episode if the initial tuple
  is rare; episodes still open at the end close truncated. It cannot overlap
  with either element route, because every full-scenario tuple is all-known.
- **Expected values** (analytical_model.py): time fraction in rare tuples
  = calibrated mass (exact in expectation); E[duration] ~= 1/tuple-change-
  rate; E[episodes] ~= T * tuple-change-rate * mass (entry-rate
  approximation, ~10%, because rare-set membership correlates with
  slow-layer states).
- **Historical results:** `results/` predates this configuration and is
  not valid for it until regenerated; the delivered v4 run is in
  `results_full_scenario/`.
