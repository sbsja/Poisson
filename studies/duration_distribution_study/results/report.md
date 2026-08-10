# Duration Distribution Study

Compares ten positive sojourn families. Nine alternatives match every element's configured mean and variance to the production Gamma law.

## Design

- Levels: 10
- Paired independent seed sets per level: 3
- All seven simulator seeds are shifted together between replicates.
- All levels within a replicate use the same seed set.
- Default screening duration: 1000 simulated hours.
- Total wall time: 73.2 seconds.

## Aggregate results

| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |
|---|---:|---:|---:|---:|---:|
| gamma | 0.02 | 0.0001333 | 47.6747 | 0.5402 | 19.3333/0.6667/0/0 |
| weibull | 0.026 | 0.0001392 | 41.5 | 1 | 25/1/0/0 |
| lognormal | 0.0213 | 0.0001083 | 27.7424 | 0.5383 | 21/0.3333/0/0 |
| inverse_gaussian | 0.0223 | 0.0001352 | 41.1681 | 1.8723 | 21.3333/1/0/0 |
| shifted_exponential | 0.027 | 0.000148 | 33.182 | 1.9678 | 26.6667/0.3333/0/0 |
| inverse_gamma | 0.0217 | 0.0001222 | 42.1544 | 1.0842 | 20.6667/1/0/0 |
| symmetric_two_point | 0.0277 | 0.0001645 | 43.0357 | 1.5635 | 27/0.6667/0/0 |
| three_point | 0.0247 | 0.0001259 | 37.5912 | 1.3906 | 24.6667/0/0/0 |
| pareto | 0.024 | 0.000144 | 46.7253 | 1.2705 | 22.6667/0.6667/0.6667/0 |
| scaled_beta | 0.0297 | 0.0001441 | 40.8849 | 2.1862 | 28.3333/1.3333/0/0 |

## Interpretation note

These are screening simulations, not causal claims from a single run. Compare the level-to-level change with the replicate standard deviations in `summary.csv`; confirm influential settings with longer runs and more seeds.

## Files

- `baseline_config.json`: immutable source configuration snapshot.
- `study_definition.json`: levels and execution settings.
- `runs.csv`: one row per simulation.
- `summary.csv` and `summary.json`: aggregate and machine-readable results.
- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.
- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.
- `duration_distribution_study_effects.png`: principal outcomes by level.

## Additional study-specific charts

- `paired_replicate_responses.png`
- `c_size_composition.png`
- `mechanism_relationships.png`
- `normalized_response_heatmap.png`
