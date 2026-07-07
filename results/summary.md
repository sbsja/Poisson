# Layered Scenario Simulation - Results Summary

## Run parameters

- target mileage: 2,000,000 miles at 50.0 mph constant average speed
- seeds: {"element_count": 12345, "rarity_assignment": 23456, "transition_matrix": 34567, "duration": 45678, "initial_state": 56789, "transition_sampling": 67890}
- global_seed (hash-based unknown combinations): 42
- unknown_weight_mode: calculated (target_unknown_element_probability = 0.004)
- unknown_combination_probability: 0.005
- concentration_scale: 100.0, allow_self_transition: True

## Totals

- total simulated mileage: 2,000,000.1 miles
- total simulated time: 144,000,004.0 s (40,000.0 h)
- event-driven steps: 9,998,505
- scenario tuple changes: 9,688,848
- wall-clock runtime: 27.5 s

## Unknown scenario encounters

- total unknown scenario encounters: 141,739
  - via unknown element: 93,615
  - via unknown combination (hash): 48,124
- estimated unknown encounter rate per million miles: 70,869.5
- first encounter at mile 19.75, last at mile 1,999,949.95
- inter-arrival distance (miles): mean 14.110, median 0.605, p90 45.387, min 0.000, max 324.575
- inter-arrival time (seconds): mean 1,015.9, median 43.6, p90 3,267.9, min 0.0, max 23,369.4
  (first inter-arrival = distance/time from the start of the simulation to the first encounter; the mileage and time position of every encounter is in encounters.csv)

## Unknown encounters per mileage window

- window size: 10,000 miles (200 complete windows; per-window counts in windows.csv)
- empirical mean count per window: 708.695
- empirical variance of count per window: 8,780.535
- dispersion index (variance / mean): 12.390 (1 = Poisson-like; > 1 = clustered/overdispersed, expected here because encounters burst while a slow layer holds an unknown element)

## Per-layer statistics

| layer | elements | common/medium/rare/very_rare/unknown | unknown_weight | designed unk. mass | realized unk. mass (Dirichlet) | empirical unk. selection rate | transitions | mean duration cfg/emp (s) |
|---|---|---|---|---|---|---|---|---|
| street | 76 | 38/19/8/4/7 | 0.02669 | 0.4000% | 0.5160% | 0.5125% | 479,981 | 300/300.0 |
| temporal_modifications | 96 | 48/24/10/5/9 | 0.02622 | 0.4000% | 0.0047% | 0.0033% | 239,845 | 600/600.4 |
| ego_maneuver | 50 | 25/13/5/2/5 | 0.02471 | 0.4000% | 0.4169% | 0.4129% | 4,797,500 | 30/30.0 |
| ru_maneuver | 69 | 35/17/7/3/7 | 0.02443 | 0.4000% | 0.0037% | 0.0042% | 3,201,552 | 45/45.0 |
| environmental_conditions | 73 | 37/18/7/4/7 | 0.02583 | 0.4000% | 0.0301% | 0.0325% | 79,956 | 1800/1801.0 |
| triggering_conditions | 62 | 31/16/6/3/6 | 0.02550 | 0.4000% | 0.0028% | 0.0026% | 1,199,671 | 120/120.0 |

## Verification against configured targets

- overall unknown-element selection rate across all transitions: 0.2247% (design target 0.40%; per-layer rates scatter around the target because each layer's transition vector is a single Dirichlet draw with concentration_scale=100.0 - increase concentration_scale for tighter adherence)
- unknown-combination rate among all-known tuple changes: 0.5015% (target 0.50%)
- empirical mean durations per layer are listed above and should be close to the configured means (Gamma parameterization: shape = mean^2/var, scale = var/mean).
- time/mileage consistency: 2,000,000.1 mi / 50.0 mph = 40,000.0 h expected, 40,000.0 h simulated.
