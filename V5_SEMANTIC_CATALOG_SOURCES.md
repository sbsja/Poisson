# Version 5 Semantic Catalog Source Register

## Purpose and scope

This document records the external sources consulted when comparing the number
of semantic elements in the version 5 scenario layers with standards,
taxonomies, research papers, and simulator catalogs.

The sources do not provide a universal required number of elements. They use
different abstraction levels: some define broad categories, while others
enumerate detailed variants. The comparisons below are therefore indicators of
catalog granularity, not proof that a catalog is complete or statistically
representative of real-world driving.

Sources and links were checked on **2026-07-27**.

## Comparison summary

| Project layer | Version 5 count | External comparison | Interpretation |
|---|---:|---:|---|
| `street` | 12 | No canonical count | Project-specific route-composition catalog |
| `temporal_modifications` | 16 | 4 broad ASAM classes; 54 detailed MUTCD applications | Intermediate abstraction level |
| `ego_maneuver` | 13 | 7 in IGP2; approximately 22 named variants in the TUM taxonomy | Within the low-tens range used by published catalogs |
| `ru_maneuver` | 14 | Approximately 22 named variants in the TUM taxonomy | Coarser by about 36% |
| `environmental_conditions` | 13 | 22 named CARLA presets, excluding `Default` | Fewer flat states, but not directly equivalent |
| `triggering_conditions` | 11 | 87 conditions in one system-specific perception ontology | Much coarser starter catalog |

## Primary sources used in the comparison

### 1. Six-Layer Model for a Structured Description of Urban Traffic and Environment

- **Authors:** Scholtes et al.
- **Publisher/source:** IEEE Access / RWTH Aachen University repository
- **Link:** <https://publications.rwth-aachen.de/record/818347/files/818347.pdf>
- **Used for:** Understanding how road-network and traffic-guidance information
  is organized in a layered scenario description.
- **Finding:** The model describes street information categorically but does
  not prescribe a fixed, canonical number of street elements. Consequently,
  the project's 12 street elements cannot be validated by count alone.

### 2. ASAM OpenODD representation of the ISO 34503 taxonomy

- **Organization:** Association for Standardization of Automation and Measuring
  Systems (ASAM)
- **Version:** ASAM OpenODD 1.0.0
- **Link:** <https://publications.pages.asam.net/standards/ASAM_OpenODD/ASAM_OpenODD/latest/specification/11_annexes/11_e_iso34503_02_openscenario_dsl.html>
- **Used for:** Temporary road structures and the structure of environmental
  conditions.
- **Findings:**
  - The published mapping contains four broad temporary-road-structure values:
    `construction_site_detour`, `refuse_collection`, `road_work`, and `signage`.
  - Environmental conditions are multidimensional and include weather,
    particulates, illumination, and connectivity.
  - Weather is further divided into temperature, wind, rainfall, and snowfall.
- **Interpretation:** The project's 16 temporal elements are more detailed than
  the four broad temporary-road classes. Its 13 environmental states are a
  flatter and simpler representation than the ISO/OpenODD hierarchy.

### 3. Manual on Uniform Traffic Control Devices, Part 6

- **Organization:** United States Department of Transportation, Federal Highway
  Administration (FHWA)
- **Edition:** MUTCD 11th Edition with Revision 1
- **Current-edition page:** <https://mutcd.fhwa.dot.gov/>
- **Part 6 PDF:** <https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part6.pdf>
- **Used for:** Detailed temporary traffic-control applications.
- **Finding:** Part 6 enumerates 54 typical applications, TA-1 through TA-54.
- **Interpretation:** The project's 16 temporal elements are 38 fewer, or about
  70% fewer, than this detailed layout catalog. This is a large numerical
  difference but is expected if each project element groups several MUTCD
  applications under one semantic category.

### 4. Interpretable Goal-based Prediction and Planning for Autonomous Driving

- **Authors:** Albrecht et al.
- **Short name:** IGP2
- **Link:** <https://sorinmd.github.io/files/papers/igp2.pdf>
- **Alternative record:** <https://arxiv.org/abs/2002.02277>
- **Used for:** A compact ego-vehicle maneuver library.
- **Finding:** The maneuver set contains seven core maneuver types: lane
  following, left and right lane changes, left and right turns, giving way, and
  stopping.
- **Interpretation:** The project's 13 ego maneuvers are six more than this
  compact library but remain at a comparable low-tens level.

### 5. Classification of Driving Maneuvers in Urban Traffic for Parametrization of Test Scenarios

- **Authors:** Hartjen et al.
- **Publisher/source:** Technical University of Munich repository
- **Link:** <https://mediatum.ub.tum.de/doc/1535131/1535131.pdf>
- **Used for:** A more detailed maneuver taxonomy for ego vehicles and other
  traffic participants.
- **Finding:** Counting named directional variants gives approximately 22
  entries across vehicle-state, infrastructure-related, and object-related
  maneuver dimensions. These dimensions can occur simultaneously, so the total
  is not a mutually exclusive one-layer catalog.
- **Interpretation:** The project has fewer maneuver labels, but the difference
  is partly caused by modeling several concurrent dimensions as one semantic
  layer.

### 6. CARLA `WeatherParameters` source catalog

- **Organization:** CARLA Simulator project
- **Link:** <https://carla.org/Doxygen/html/da/d0c/LibCarla_2source_2carla_2rpc_2WeatherParameters_8h_source.html>
- **Used for:** Comparing named environmental/weather presets.
- **Finding:** The current source lists 22 named weather presets when `Default`
  is excluded: seven noon presets, seven sunset presets, seven night presets,
  and `DustStorm`.
- **Interpretation:** The project's 13 environmental conditions are nine fewer,
  or about 41% fewer. The comparison is not one-to-one because CARLA presets
  combine time of day with weather, whereas the project catalog also contains
  separate concepts such as surface condition, glare, snow, ice, and wind.

### 7. ISO 21448:2022 — Road Vehicles: Safety of the Intended Functionality

- **Organization:** International Organization for Standardization (ISO)
- **Link:** <https://www.iso.org/standard/77490.html>
- **Used for:** Establishing the standards context for triggering conditions.
- **Finding:** ISO 21448 defines the SOTIF safety framework but does not publish
  a universal required number of triggering conditions.
- **Interpretation:** A project's triggering-condition count must be justified
  against its functions, sensors, ODD, and insufficiency analysis rather than a
  fixed ISO count.

### 8. An Ontology-based Method to Identify Triggering Conditions for Perception Insufficiency of Autonomous Vehicles

- **Authors:** Xing et al.
- **Link:** <https://arxiv.org/abs/2210.08724>
- **Used for:** A detailed, system-specific triggering-condition comparison.
- **Finding:** The study identified 87 triggering conditions for a Level 3
  perception system. It field-tested 20 of them, with eight reported as causing
  risky behavior in the evaluated system.
- **Interpretation:** The project's 11 entries are 76 fewer, or about 87% fewer.
  The 87-condition result is not a universal target; it demonstrates how much a
  top-level trigger catalog can expand when tied to a particular perception
  architecture.

## Additional sources consulted

These sources provided context or cross-checks but were not used as direct
one-to-one numerical targets in the final layer-count table.

### MUTCD 2009, Part 6, Chapter 6H

- **Organization:** FHWA
- **Link:** <https://mutcd.fhwa.dot.gov/htm/2009/part6/part6h.htm>
- **Use:** Historical cross-check. The older edition enumerated 46 typical
  applications, showing that the number of detailed temporary-control layouts
  changes between MUTCD editions.

### ISO 34503:2023 — Taxonomy for Operational Design Domain for an Automated Driving System

- **Organization:** ISO
- **Link:** <https://www.iso.org/standard/78952.html>
- **Use:** Official scope and metadata for the ODD taxonomy represented in the
  ASAM OpenODD annex. The full taxonomy details used in this comparison came
  from the openly accessible ASAM representation.

### PAS 1883:2020 — Operational Design Domain Taxonomy for an Automated Driving System

- **Organization:** British Standards Institution (BSI)
- **Link:** <https://www.bsigroup.com/globalassets/localfiles/en-gb/cav/pas1883.pdf>
- **Use:** Cross-checking hierarchical environment concepts, including
  particulates, weather, and illumination. It supports using environmental
  dimensions instead of treating all conditions as mutually exclusive states.

### Identifying Novel SOTIF Triggering Conditions through Feature Interaction

- **Authors:** Adee et al.
- **Link:** <https://arxiv.org/abs/2303.04037>
- **Use:** Supporting the observation that triggering-condition identification
  is open-ended and system-dependent rather than governed by a canonical list.

### Triggering Conditions Analysis and Use Case for Validation of ADAS/ADS Functions

- **Authors:** Expósito Jiménez et al.
- **Link:** <https://arxiv.org/abs/2302.00551>
- **Use:** Background on deriving and analyzing triggering conditions for
  ADAS/ADS validation.

### Quantifying the Complexity of Standard Benchmarking Datasets for Long-Term Human Driving Behavior

- **Publisher:** Nature Communications
- **Link:** <https://www.nature.com/articles/s41467-021-21007-8>
- **Use:** Cross-checking how real driving behavior can be grouped into exposure
  classes such as free driving, car following, cut-in, and lane-change contexts.
  It was not used as the numerical target for the maneuver catalogs.

## Limitations and evidence boundary

- The project has no real driving dataset, so none of these sources calibrates
  real-world occurrence probabilities for the catalog elements.
- Percent differences compare label counts, not equivalent statistical or
  semantic units.
- Simulator presets, standards taxonomies, maneuver libraries, and test-layout
  manuals serve different purposes and should not be treated as interchangeable.
- Catalog completeness must be assessed through definition coverage,
  traceability, scenario generation tests, and system-specific hazard analysis,
  not by matching one source's element count.
- The version 5 semantic IDs, groupings, and rarity labels remain project
  engineering decisions even where their terminology is informed by these
  sources.
