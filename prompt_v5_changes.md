# Change Request v5 — Fixed Semantic Element Catalogs

## Goal

Replace seed-dependent generated identifiers in the default configuration
with stable, meaningful scenario-element IDs. The project has no real driving
data, so v5 improves interpretability and reproducibility without claiming
empirical calibration.

## Configuration

Non-street layers may use a `semantic_catalog` containing a version and an
ordered element list. Every element has a stable snake-case `id`, label,
description, and rarity. A layer uses exactly one construction form:

1. `fixed_elements` with exact probabilities;
2. `semantic_catalog` with rarity-based weights; or
3. legacy `element_count_min` / `element_count_max` generation.

The default config uses catalog version `1.0` for all five non-street layers.
Street remains the fixed 12-element route-composition layer.

## Probability behavior

Catalog order and rarity labels are deterministic and do not consume the
`element_count` or `rarity_assignment` RNG streams. Rarity weights, calculated
unknown weights, Dirichlet transition-vector draws, duration sampling, episode
semantics, and full-scenario classification remain unchanged. Every default
unknown-bearing catalog has exactly 0.4% designed unknown mass.

## Stable rules and outputs

Conditional rules now reference IDs such as `merge`, `fog`, and
`sensor_occlusion`. JSON layer statistics include catalog version,
construction mode, and per-element metadata with visit count and realized
selection rate. `episodes.csv` retains its existing columns and appends label,
description, and catalog version.

## Compatibility

Legacy generated-layer configurations remain valid. Invalid mixed
construction forms, duplicate IDs, malformed IDs, missing metadata, invalid
rarities, and inconsistent unknown settings fail configuration validation.

## Assumption boundary

Catalog contents and rarity assignments are engineering choices informed by
the existing project research and common AV/ODD terminology. They are not
measured occurrence rates. See `SEMANTIC_CATALOGS.md` for definitions,
rationale, and versioning policy.
