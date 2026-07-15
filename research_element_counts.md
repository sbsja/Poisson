# Research: Element Counts per Layer

Task (change request §3): find defensible element counts per layer from
literature/standards, convert to per-layer `[min, max]` ranges, cite
sources, and say explicitly where no defensible number exists instead of
assuming one. Street is fixed by user-supplied route-composition data
(§6); triggering_conditions is deliberately left unchanged (§5).

## Summary of adopted ranges

| layer | range | basis |
|---|---|---|
| street | 12 (fixed list) | user route-composition data, not researched |
| temporal_modifications | [30, 46] | max anchored; **min is a flagged modeling choice** |
| ego_maneuver | [7, 12] | anchors are 7 and 14; **clipped to 12 for feasibility, see below** |
| ru_maneuver | [7, 12] | anchors are 7 and 14; **clipped to 12 for feasibility, see below** |
| environmental_conditions | [15, 21] | both ends anchored |
| triggering_conditions | [50, 100] | unchanged by design (§5); realistic count to be investigated later |

**Feasibility clip for ego/RU maneuvers.** With the assignment's fixed
proportions (10% unknown), base weights, and 0.4% target, layers of 13 or
14 elements get exactly one unknown element by largest-remainder rounding,
and the calculated unknown weight would have to be 0.0335–0.0351 — larger
than the very_rare weight (0.03), which the specification forbids. The
configured ranges are therefore clipped to [7, 12] (all n in a configured
range are now feasibility-checked at config validation). To use the full
researched maximum of 14, either lower
`target_unknown_element_probability` (≤ ~0.0034) or switch
`unknown_weight_mode` to `"fixed"`.

## Findings per layer

### Temporal modifications (work zones, temporary traffic management)

The strongest enumerable source is the US **MUTCD, Part 6 (Temporary
Traffic Control), Chapter 6H**: Table 6H-1 indexes exactly **46 "typical
applications"** (TA-1…TA-46) — standard work-zone layouts organized by
duration, location, type of work, and highway type. We adopt 46 as the
upper bound. **No defensible lower bound was found in the literature**;
the adopted minimum of 30 is a modeling choice (representing deployments
whose ODD excludes some layout families, e.g. flagger- or
freeway-specific ones) and is flagged as such rather than presented as
evidence-based.

### Ego maneuver

Maneuver taxonomies in the literature span a consistent, small range:

- Albrecht et al., *Interpretable Goal-based Prediction and Planning*
  (IGP2), use a finite maneuver library of ~7 (lane-follow, lane-change
  left/right, turn left/right, give-way, stop).
- The TUM classification of driving maneuvers in urban traffic structures
  basic maneuvers into vehicle-state (accelerate, keep velocity,
  decelerate, reverse), infrastructure-related, and traffic-relation
  categories — order of 10 basic maneuvers.
- A survey of vision-driven driving datasets reports **14
  maneuver classes** as the upper end used in real-world studies.

Adopted range: **[7, 14]**, both ends anchored.

### RU (road user) maneuver

The same maneuver taxonomies apply to surrounding vehicles; the survey's
**14 surrounding-vehicle maneuvers in real-world highway scenes** anchors
the maximum, and the ~7-maneuver core set the minimum. Adopted range:
**[7, 14]**. Open refinement (flagged, not included): dedicated VRU
action classes (crossing, walking along carriageway, waiting) would push
the maximum a few elements higher; no citable combined count was found.

### Environmental conditions (weather layer)

- Lower anchor: the **CARLA simulator ships exactly 15 weather presets**
  (ClearNoon … SoftRainSunset), a de-facto practice standard for
  discretized environmental conditions in AV simulation.
- Upper anchor: a leaf-level enumeration of the **BSI PAS 1883:2020**
  environment taxonomy (from the published PAS document): rainfall
  intensity 3 classes (light/moderate/heavy) + snowfall 3 classes
  (visibility-based light/moderate/heavy) + wind ~3 specified m/s bands +
  particulates 4 classes (marine, non-precipitating droplets i.e.
  fog/mist, sand/dust, smoke) + illumination: day 3 sun-elevation bands,
  night 1, cloudiness ~3 okta bands, artificial illumination 1 —
  ≈ **21 discrete condition leaves** (exact number depends on banding
  granularity; the derivation above is what we count).

Adopted range: **[15, 21]**, both ends anchored. Note: this layer
contains no unknown elements (change request §7).

### Street — not researched

Fixed at the 12 user-supplied route-composition elements with exact
transition probabilities (change request §6).

### Triggering conditions — not researched (by design)

Left at [50, 100] per §5. Honest note: the SOTIF literature (e.g.
Expósito Jiménez et al., *Triggering Conditions Analysis for ADAS/ADS*)
builds triggering-condition lists from ODD taxonomies but does not state
a canonical count; a defensible number for this layer does not currently
exist, which is consistent with investigating it separately later.

## Consequence for the scenario space

With the new counts the scenario-tuple space is roughly
12 × [30–46] × [7–14] × [7–14] × [15–21] × [50–100] ≈ 1.3 × 10⁷ … 9 × 10⁷
possible tuples (vs ~10¹¹ before).

## Sources

- [MUTCD 2009, Part 6, Chapter 6H — Typical Applications (Table 6H-1, TA-1…TA-46)](https://mutcd.fhwa.dot.gov/htm/2009/part6/part6h.htm)
- [MUTCD 11th edition, Part 6 (PDF)](https://mutcd.fhwa.dot.gov/pdfs/11th_Edition/part6.pdf)
- [Albrecht et al., Interpretable Goal-based Prediction and Planning for Autonomous Driving (IGP2)](https://arxiv.org/pdf/2002.02277)
- [Classification of Driving Maneuvers in Urban Traffic for Parametrization of Test Scenarios (TUM)](https://mediatum.ub.tum.de/doc/1535131/1535131.pdf)
- [What Demands Attention in Urban Street Scenes? — survey reporting 14 surrounding-vehicle maneuver classes](https://arxiv.org/pdf/2507.06513)
- [CARLA Python API — 15 WeatherParameters presets](https://carla.readthedocs.io/en/0.9.3/python_api_tutorial/)
- [CARLA WeatherParameters source (preset list)](https://github.com/carla-simulator/carla/blob/master/LibCarla/source/carla/rpc/WeatherParameters.h)
- [BSI PAS 1883:2020 — ODD taxonomy for an ADS (environment section)](https://www.bsigroup.com/globalassets/localfiles/en-gb/cav/pas1883.pdf)
- [Scholtes et al., 6-Layer Model for a Structured Description of Urban Traffic and Environment](https://publications.rwth-aachen.de/record/818347/files/818347.pdf)
- [Expósito Jiménez et al., Triggering Conditions Analysis and Use Case for Validation of ADAS/ADS Functions](https://www.researchgate.net/publication/367961992_Triggering_Conditions_Analysis_and_Use_Case_for_Validation_of_ADASADS_Functions)
