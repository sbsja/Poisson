# Change Request v4 — Conditional Transition Model Between Layers

Fourth change-request document (v1 = original assignment in chat; v2 =
`prompt_v2_changes.md`; v3 = `prompt_v3_changes.md`, full-scenario rarity).

**Status: IMPLEMENTED and AUDITED** — implemented in the working tree
(simulator.py `ConditionSelector` / `ConditionalRule` /
`ConditionalTransitionModel`, `transition_model` config block); audit
confirmed the implementation matches this specification; 61 tests pass.
See the audit summary at the end.

---

## Task

Support configurable conditional behavior between layers while preserving
the existing independent model as a fully backward-compatible option.

## Transition-model modes

1. **independent** — preserves current behavior exactly: each layer's
   permanent transition vector, no cross-layer influence. Configurations
   omitting the new block default to independent; configuration, seeds,
   RNG consumption, checkpoint behavior, and results remain bit-identical.
2. **conditional** — reweights a target layer's base next-element
   probabilities using rules matching the current states of other layers;
   normalized before sampling; uses the existing `transition_sampling`
   RNG; rule evaluation itself consumes no randomness.

## Configuration

```yaml
transition_model:
  mode: independent   # "independent" | "conditional"
  conditional:
    apply_to_initial_state: true
    rules:
      - id: merge_affects_ego
        target_layer: ego_maneuver
        when:
          street:
            elements: [forced_merge_proceeding, forced_merge_merging]
          environmental_conditions:
            rarities: [rare, very_rare]
        multipliers:
          elements: {ego_003: 4.0}
          rarities: {common: 0.7, rare: 1.5}
```

## Rule semantics

adjusted_weight[i] = base_probability[i] × Π(applicable element
multipliers) × Π(applicable rarity multipliers); then normalize. Multiple
rules on the same target combine multiplicatively. Conditions: AND across
layers inside `when`; OR among `elements`/`rarities` within one layer
(including between the two lists). Non-matching rules have no effect; an
element may receive both an element and a rarity multiplier; 1.0 is a
no-op; zero multipliers may prohibit transitions but a context zeroing the
entire target distribution is rejected; negative, non-finite, boolean, or
non-numeric multipliers are rejected.

## Dependency ordering

Condition layer → target layer edges must form an acyclic graph. Rejected:
self-conditioning, direct/indirect cycles, unknown layers/elements/
rarities, duplicate rule IDs, empty conditions or effects. Simultaneously
expired layers are processed in topological order (already-sampled parents
expose their new values; non-expired parents their current values; ties
between unrelated layers use the fixed layer order); episode changes
commit per sampled transition in that order; full-tuple mechanisms are
evaluated only after all expired layers are updated. Rule-list order in
YAML cannot affect results (rules are ID-sorted at compile time).

## Initial states

With conditional mode and `apply_to_initial_state: true`, initial states
sample in topological order (roots from their existing initial
distributions, dependents reweighted) using only the existing
`initial_state` RNG. With `false`, the original fixed-order sampling is
preserved.

## Self-transitions

Conditional mode with `allow_self_transition: false`: the current
element's adjusted weight is zeroed and the rest renormalized; an empty
remainder raises a clear error. Independent mode keeps the original
rejection sampling untouched (bit-identical requirement).

## Unknown probabilities

`target_unknown_element_probability` is the construction-time baseline
only. Conditional rules may change context-specific and overall unknown
rates; outputs report baseline unknown mass, realized unconditional
unknown occupancy, conditional selection rate, rule match counts, and
rule-influenced transition counts. The summary warns when rules modify
unknown-rarity elements.

## Full-scenario compatibility

The independent-product P(S) classifier is invalid under conditional
dynamics: `transition_model.mode: conditional` together with
`full_scenario_unknowns.enabled: true` is rejected with an explanatory
error. Dependency-aware full-scenario rarity calibration is documented as
future work.

## Outputs

stats.json / summary.md include: mode, whether conditional initialization
was used, dependency order, per-rule ID/target/match counts, number of
modified-distribution transitions, target-layer selections under matched
vs unmatched contexts, and baseline vs empirical unknown mass per layer —
kept separate from episode counts.

## Validation and tests (all present, 61 passing)

Omitted block defaults to independent; explicit independent bit-identical
(events, episodes, visit counts); independent mode neither compiles nor
evaluates dormant rules (proved with an intentionally invalid dormant
rule); matching/non-matching reweighting against hand-computed vectors;
element+rarity multiplier combination; multiplicative multi-rule
combination with YAML-order independence; AND/OR semantics; conditional
initialization order; simultaneous expiries see new parent state; cycles
and self-dependencies rejected (parametrized); invalid references and
multipliers rejected; zeroed distributions rejected; self-transition
exclusion after reweighting; conditional checkpoint/resume bit-identical;
conditional+full-scenario rejection; diagnostics and unknown-modification
warning in outputs; all pre-existing tests unchanged and passing.

## Audit summary (independent verification)

- Omitted `transition_model` → independent mode: verified.
- Hand-computed conditional vector (element × rarity multipliers,
  normalization) matches `probabilities_for` to 1e-14: verified.
- Non-matching context returns the normalized base vector: verified.
- Conditional + full-scenario rejection: verified.
- Conditional runs deterministic for fixed config/seeds: verified.
- Independent hot path is the original code path (original expired-layer
  iteration and rejection sampling), so bit-identical preservation holds
  structurally as well as by test.

Caveats documented in README/config comments: conditional probabilities do
not by themselves create causal validity (rule values need calibration),
and generated element names (e.g. `ego_003`) are seed-dependent — exact
element rules should preferably use fixed, versioned, named element
catalogs.
