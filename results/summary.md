# Layered Scenario Simulation - Results (episode semantics)

## Run parameters

- target mileage: 2,000,000 miles at 50.0 mph constant average speed
- seeds: {"element_count": 12345, "rarity_assignment": 23456, "transition_matrix": 34567, "duration": 45678, "initial_state": 56789, "transition_sampling": 67890, "pattern_rules": 78901}
- unknown combinations: ENABLED (hash threshold 0.005, global_seed 42; pattern rules from config + seeds.pattern_rules)
- unknown_weight_mode: calculated (target_unknown_element_probability = 0.004)
- concentration_scale: 20,000 (see concentration_study.md), allow_self_transition: True

## Totals

- total simulated mileage: 2,000,000.1 miles
- total simulated time: 144,000,004.0 s (40,000.0 h)
- event-driven steps: 9,998,505
- wall-clock runtime: 46.2 s

## Unknown episodes

- total unknown episodes: 84,296 (of which truncated at simulation end: 0)
- by type: element 39,227, pattern 3,476, hash combination 41,593
  - element durations (s): mean 60.5, median 33.8, p90 106.7, max 2,435.9
  - pattern durations (s): mean 261.0, median 204.5, p90 541.1, max 1,812.3
  - hash_combination durations (s): mean 16.7, median 13.3, p90 35.4, max 131.0
- episodes per 1,000,000 miles: 42,148.00
- episodes by layer: temporal_modifications: 977, ego_maneuver: 21,018, ru_maneuver: 12,217, triggering_conditions: 5,015
- total time in unknown scenario (union of episodes): 3,946,822.1 s = 2.7408% of simulated time
- episode duration (seconds): mean 47.2, median 22.0, p90 84.1, max 2,435.9
- episode duration (miles): mean 0.655, median 0.305, p90 1.168, max 33.832
- inter-arrival distance between episode starts (miles): mean 23.7, median 16.1, p90 55.6, max 307.4
- inter-arrival time between episode starts (seconds): mean 1,708.3, median 1,157.0, p90 4,004.4, max 22,130.9
  (first inter-arrival measured from the start of the simulation; every episode's mileage/time position is in episodes.csv)

## Episode starts per mileage window

- window size: 10,000 miles (200 complete windows; counts in windows.csv)
- empirical mean count per window: 421.480
- empirical variance of count per window: 531.567
- dispersion index (variance / mean): 1.261 (~1 = Poisson-like; episode STARTS are near-Poisson because each start is an independent rare transition, unlike the old per-tuple encounter counting)

## Per-layer statistics

| layer | elements | c/m/r/vr/unknown | unknown_weight | designed unk. mass | realized unk. mass | empirical unk. selection | episodes | transitions | mean duration cfg/emp (s) |
|---|---|---|---|---|---|---|---|---|---|
| street (fixed) | 12 | 2/4/3/3/0 | - | 0.0000% | 0.0000% | 0.0000% | 0 | 479,981 | 300/300.0 |
| temporal_modifications | 43 | 22/11/4/2/4 | 0.02697 | 0.4000% | 0.4077% | 0.4086% | 977 | 239,845 | 600/600.4 |
| ego_maneuver | 12 | 6/3/1/1/1 | 0.02944 | 0.4000% | 0.4369% | 0.4401% | 21,018 | 4,797,500 | 30/30.0 |
| ru_maneuver | 7 | 3/2/1/0/1 | 0.01566 | 0.4000% | 0.3846% | 0.3831% | 12,217 | 3,201,552 | 45/45.0 |
| environmental_conditions | 21 | 12/6/2/1/0 | - | 0.0000% | 0.0000% | 0.0000% | 0 | 79,956 | 1800/1801.0 |
| triggering_conditions | 69 | 35/17/7/3/7 | 0.02443 | 0.4000% | 0.4197% | 0.4184% | 5,015 | 1,199,671 | 120/120.0 |

## Verification against configured targets

- unknown-element selection rate across unknown-bearing layers: 0.4172% (design target 0.40%; per-layer adherence is tight at concentration_scale=20,000)
- pattern rules (episodes vs mass*T*hazard expectation in analytical_model.md): [manual] street=forced_merge_merging & environmental_conditions=environment_000 (mass 0.0696%, episodes 367); [generated] street=lane_split_proceeding & temporal_modifications=temporal_024 (mass 0.2684%, episodes 1,834); [generated] street=lane_split_exiting & triggering_conditions=trigger_066 (mass 0.0328%, episodes 508); [generated] temporal_modifications=temporal_000 & environmental_conditions=environment_007 (mass 0.2549%, episodes 767)
- street composition, empirical visit share vs configured probability (top 5): constant_lane 49.377% vs 49.3%; forced_merge_proceeding 16.904% vs 16.9%; overlap_zone 9.440% vs 9.5%; road_split_proceeding 7.869% vs 7.9%; lane_split_proceeding 7.214% vs 7.2%
- street and environmental_conditions contain no unknown elements (episodes: 0 and 0); episodes originate only in the other four layers, as specified
- time/mileage consistency: 2,000,000.1 mi / 50.0 mph = 40,000.0 h expected, 40,000.0 h simulated.
