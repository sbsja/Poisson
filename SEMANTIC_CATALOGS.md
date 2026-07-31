# Semantic Element Catalogs

## Purpose and evidence boundary

Version 5 replaces anonymous generated IDs with stable semantic IDs. This
repository has no real driving dataset, so the catalogs provide a reviewable
scenario vocabulary rather than empirically calibrated frequencies. Rarity
labels, duration parameters, and resulting probabilities remain engineering
assumptions and must be evaluated through sensitivity studies.

The terminology follows the sources already summarized in
`research_element_counts.md`: the six-layer scenario model, MUTCD temporary
traffic-control applications, published maneuver taxonomies, CARLA weather
concepts, PAS 1883 ODD terminology, and SOTIF triggering-condition literature.
The exact grouping and rarity assigned to each v1.0 entry are project choices.

## Catalogs in version 1.0

| Layer | Size | Unknown entry | Engineering rationale |
|---|---:|---|---|
| temporal_modifications | 16 | `unclassified_temporal_modification` | Groups common temporary traffic-control layouts and activities into stable operational concepts. |
| ego_maneuver | 13 | `unclassified_ego_maneuver` | Covers longitudinal, lateral, junction, merge/diverge, yielding, and emergency behavior. |
| ru_maneuver | 14 | `unclassified_road_user_maneuver` | Covers ordinary progress plus interaction-oriented surrounding-road-user maneuvers. |
| environmental_conditions | 13 | none | Covers lighting, precipitation, visibility, surface condition, and wind; the layer remains known-only by design. |
| triggering_conditions | 11 | `unclassified_triggering_condition` | Covers perception, map, signage, geometry, unusual-object, and interference triggers. |

The authoritative IDs, labels, descriptions, ordering, and rarity assignments
are in `config.yaml`. Street remains a separate fixed-probability catalog from
the user-provided route-composition data.

## Versioning policy

- IDs are stable API identifiers. Do not rename or reuse an ID with a new
  meaning within a catalog version.
- Labels and descriptions may receive spelling-only corrections without a
  catalog-version change; semantic changes require a version increment.
- Adding, removing, splitting, merging, reordering, or changing the rarity of
  an element requires a new catalog version and regenerated results.
- Deprecate an ID by retaining it for compatibility and documenting its
  replacement before removing it in a later major catalog version.
- Conditional rules and downstream analysis must reference IDs, not labels or
  numeric positions.
- Simulator version and catalog version are independent. Simulator v5 ships
  catalog version `1.0`.

## Probability interpretation

For a semantic catalog, rarity labels select the configured base weights. If
unknown entries exist, their weight is calculated so the catalog's designed
unknown mass equals `target_unknown_element_probability`. A permanent
transition vector is then drawn from the same Dirichlet model used previously.
The semantic catalog therefore stabilizes identity; it does not turn assumed
weights into observed real-world probabilities.

## Extending a catalog safely

1. Define the new element's scope so it does not overlap existing entries.
2. Assign a stable snake-case ID, label, description, and rarity.
3. Increment the catalog version.
4. Update conditional rules and coverage tests where appropriate.
5. Run configuration validation, the full test suite, and a multi-seed
   sensitivity comparison against the previous catalog.
6. Store new results separately; do not compare raw counts across catalog
   versions without explaining the taxonomy change.
