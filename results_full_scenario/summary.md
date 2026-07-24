# Layered Scenario Simulation - Results (episode semantics)

## Run parameters

- target mileage: 2,000,000 miles at 50.0 mph constant average speed
- seeds: {"element_count": 12345, "rarity_assignment": 23456, "transition_matrix": 34567, "duration": 45678, "initial_state": 56789, "transition_sampling": 67890, "pattern_rules": 78901}
- unknown combinations: patterns disabled; hash combinations disabled (pattern rules from config + seeds.pattern_rules)
- full-scenario rarity unknowns: ENABLED - target stationary mass 0.4000%, calibrated threshold 5.691e-10, calibration samples 2,000,000 (seed 90123), achieved sampled mass 0.4000%
- unknown_weight_mode: calculated (target_unknown_element_probability = 0.004)
- concentration_scale: 20,000 (see concentration_study.md), allow_self_transition: True

## Totals

- total simulated mileage: 2,000,000.1 miles
- total simulated time: 144,000,004.0 s (40,000.0 h)
- event-driven steps: 9,998,505
- wall-clock runtime: 21.9 s

## Unknown episodes

- total unknown episodes: 75,227 (of which truncated at simulation end: 0)
- by type: element 39,227, full scenario 36,000
  - element durations (s): mean 60.5, median 33.8, p90 106.7, max 2,435.9
  - full_scenario durations (s): mean 15.8, median 12.6, p90 33.4, max 163.2
- episodes per 1,000,000 miles: 37,613.50
- episodes by layer: temporal_modifications: 977, ego_maneuver: 21,018, ru_maneuver: 12,217, triggering_conditions: 5,015
- total time in unknown scenario (union of episodes): 2,685,953.9 s = 1.8652% of simulated time
- episode duration (seconds): mean 39.1, median 21.1, p90 70.2, max 2,435.9
- episode duration (miles): mean 0.543, median 0.293, p90 0.975, max 33.832
- inter-arrival distance between episode starts (miles): mean 26.6, median 9.4, p90 77.9, max 476.1
- inter-arrival time between episode starts (seconds): mean 1,914.2, median 676.5, p90 5,610.3, max 34,280.1
  (first inter-arrival measured from the start of the simulation; every episode's mileage/time position is in episodes.csv)

## Episode starts per mileage window

- window size: 10,000 miles (200 complete windows; counts in windows.csv)
- empirical mean count per window: 376.135
- empirical variance of count per window: 1,660.117
- dispersion index (variance / mean): 4.414 (~1 = Poisson-like; episode STARTS are near-Poisson because each start is an independent rare transition, unlike the old per-tuple encounter counting)

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
- realized full-scenario unknown mass (time fraction): 0.3938% vs configured target 0.4000% (calibration is exact in expectation; single-run deviation is dominated by slow-layer correlation of rare periods)
- street composition, empirical visit share vs configured probability (top 5): constant_lane 49.377% vs 49.3%; forced_merge_proceeding 16.904% vs 16.9%; overlap_zone 9.440% vs 9.5%; road_split_proceeding 7.869% vs 7.9%; lane_split_proceeding 7.214% vs 7.2%
- street and environmental_conditions contain no unknown elements (episodes: 0 and 0); episodes originate only in the other four layers, as specified
- time/mileage consistency: 2,000,000.1 mi / 50.0 mph = 40,000.0 h expected, 40,000.0 h simulated.
