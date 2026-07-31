# High-Quality Semantic Catalog Version 2.0

## Purpose

Catalog version 2.0 increases semantic coverage while keeping every entry
meaningful, reviewable, and traceable to a published source. It uses fixed
counts: no element-count or rarity-assignment sampling occurs.

## Fixed counts

| Layer | Fixed amount | Evidence basis |
|---|---:|---|
| Street | 12 | Existing user-supplied route-composition catalog and exact probabilities |
| Temporal modifications | 45 | 41 explicit MUTCD Part 6 typical-application contexts plus 4 scoped unknown-coverage buckets |
| Ego maneuvers | 24 | All 22 named variants in the Hartjen/TUM urban maneuver taxonomy plus 2 scoped unknown buckets |
| Road-user maneuvers | 24 | The same source-backed vehicle maneuver taxonomy plus 2 scoped unknown buckets |
| Environmental conditions | 22 | The 22 named CARLA weather presets excluding `Default` |
| Triggering conditions | 50 | 45 concrete conditions derived from the Xing perception-trigger ontology and ISO/OpenODD concepts plus 5 scoped unknown buckets |

The triggering catalog is intentionally **50 rather than 80–90**. The Xing
study reports 87 conditions for one particular Level 3 perception system, but
the complete set is architecture-specific. Only conditions that can be given a
clear definition and defensible source mapping are included here.

## Primary sources

- FHWA, MUTCD 11th Edition Part 6:
  <https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part6.pdf>
- Hartjen et al., *Classification of Driving Maneuvers in Urban Traffic for
  Parametrization of Test Scenarios*:
  <https://mediatum.ub.tum.de/doc/1535131/1535131.pdf>
- CARLA `WeatherParameters` source:
  <https://carla.org/Doxygen/html/da/d0c/LibCarla_2source_2carla_2rpc_2WeatherParameters_8h_source.html>
- Xing et al., *An Ontology-based Method to Identify Triggering Conditions for
  Perception Insufficiency of Autonomous Vehicles*:
  <https://arxiv.org/abs/2210.08724>
- ASAM OpenODD representation of ISO 34503:
  <https://publications.pages.asam.net/standards/ASAM_OpenODD/ASAM_OpenODD/latest/specification/11_annexes/11_e_iso34503_02_openscenario_dsl.html>
- ISO 21448:2022 SOTIF overview:
  <https://www.iso.org/standard/77490.html>

## Quality rules enforced by the simulator

Every version 2.0 element must provide:

- a unique stable snake-case ID;
- a human-readable label;
- a non-empty operational description;
- a taxonomy family;
- one or more source-reference IDs;
- a valid rarity category.

Every source-reference ID must resolve through the catalog's `sources`
mapping. Configuration validation rejects a v2 catalog with missing families,
missing sources, duplicate references, or undefined source IDs.

## Modeling boundaries

The Hartjen taxonomy contains vehicle-state, infrastructure-related, and
object-related maneuver dimensions that may occur simultaneously. The current
simulator still selects one dominant element from each maneuver layer. Version
2.0 therefore improves vocabulary coverage but does not reproduce the source's
multi-label concurrency.

The environmental catalog follows CARLA presets so its 22 states are complete
combined presets rather than independent weather dimensions. This avoids
ambiguous simultaneous states inside the current single-choice layer.

Unknown entries are not invented real-world events. They are explicit coverage
boundaries grouped by taxonomy family so an unknown episode remains
interpretable without pretending that the missing condition has been
classified.

Rarity labels and transition probabilities remain engineering assumptions.
The project has no real driving dataset, so source-backed names improve
semantic quality and traceability but do not create empirical frequency
estimates.
