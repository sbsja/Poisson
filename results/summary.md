# Layered Scenario Simulation - Results Summary

## Run parameters

- target mileage: 2,000,000 miles at 50.0 mph constant average speed
- simulation_seed: 12345, global_seed: 42
- unknown_weight_mode: calculated (target_unknown_element_probability = 0.004)
- unknown_combination_probability: 0.005
- concentration_scale: 100.0, allow_self_transition: True

## Totals

- simulated distance: 2,000,000.0 miles
- simulated time: 144,000,002 s (40,000.0 h)
- event-driven steps: 10,002,364
- scenario tuple changes: 9,635,608
- wall-clock runtime: 26.8 s

## Unknown scenario encounters

- total encounters: 154,747
  - via unknown element: 106,898
  - via unknown combination (hash): 47,849
- encounters per 1,000,000 miles: 77,373.5
- first encounter at mile 22.72, last at mile 1,999,957.64
- inter-arrival distance (miles): mean 12.924, median 0.346, p90 44.692, min 0.000, max 402.279
  (first inter-arrival = distance from start to first encounter; full list in encounters.csv)

## Per-layer statistics

| layer | elements | common/medium/rare/very_rare/unknown | unknown_weight | designed unk. mass | realized unk. mass (Dirichlet) | empirical unk. selection rate | transitions | mean duration cfg/emp (s) |
|---|---|---|---|---|---|---|---|---|
| street | 76 | 38/19/8/4/7 | 0.02669 | 0.4000% | 0.1128% | 0.1219% | 479,965 | 300/300.0 |
| temporal_modifications | 50 | 25/13/5/2/5 | 0.02471 | 0.4000% | 0.0782% | 0.0763% | 239,943 | 600/600.1 |
| ego_maneuver | 54 | 27/14/5/3/5 | 0.02666 | 0.4000% | 0.1132% | 0.1104% | 4,800,383 | 30/30.0 |
| ru_maneuver | 67 | 33/17/7/3/7 | 0.02329 | 0.4000% | 0.0003% | 0.0004% | 3,202,926 | 45/45.0 |
| environmental_conditions | 66 | 33/16/7/3/7 | 0.02306 | 0.4000% | 0.1688% | 0.1802% | 79,913 | 1800/1802.0 |
| triggering_conditions | 64 | 32/16/7/3/6 | 0.02623 | 0.4000% | 0.6117% | 0.5982% | 1,199,234 | 120/120.1 |

## Verification against configured targets

- overall unknown-element selection rate across all transitions: 0.1340% (design target 0.40%; per-layer rates scatter around the target because each layer's transition vector is a single Dirichlet draw with concentration_scale=100.0 - increase concentration_scale for tighter adherence)
- unknown-combination rate among all-known tuple changes: 0.5022% (target 0.50%)
- empirical mean durations per layer are listed above and should be close to the configured means (Gamma parameterization: shape = mean^2/var, scale = var/mean).
- time/mileage consistency: 2,000,000.0 mi / 50.0 mph = 40,000.0 h expected, 40,000.0 h simulated.
