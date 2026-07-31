# Simulator Profiles

The repository provides two explicitly named profiles that run through the
same simulation engine. Their difference is how non-street elements are
defined and named.

## Profiles

| Profile | Configuration file | Element identity |
|---|---|---|
| **Semantic Catalog Simulator (v5-S)** | `config_semantic_catalog_v5s.yaml` | Fixed, meaningful, versioned IDs such as `lane_follow`, `cut_in`, `fog`, and `sensor_occlusion` |
| **High-Quality Semantic Catalog v2** | `config_semantic_catalog_v2.yaml` | Larger fixed catalogs with mandatory family and source traceability |
| **Generated Element Simulator (v5-G)** | `config_generated_elements_v5g.yaml` | Anonymous generated IDs such as `ego_000`, `ru_000`, `environment_000`, and `trigger_000` |

The short suffixes are deliberately different:

- **S** means semantic catalog.
- **G** means generated anonymous elements.

Both profile names are written to console output, `summary.md`, and
`stats.json`, preventing results from the two configurations from being
mistaken for each other.

## Element amounts

| Layer | v5-S semantic profile | v5-G generated profile |
|---|---:|---:|
| Street | 12 fixed route elements | Same 12 fixed route elements |
| Temporal modifications | 16 fixed semantic elements | Uniform integer from 40–45 |
| Ego maneuvers | 13 fixed semantic elements | Uniform integer from 20–24 |
| Road-user maneuvers | 14 fixed semantic elements | Uniform integer from 20–24 |
| Environmental conditions | 13 fixed semantic elements | Fixed at 22 generated elements |
| Triggering conditions | 11 fixed semantic elements | Uniform integer from 80–90 |

The separate high-quality semantic v2 profile fixes the layer counts at
12/45/24/24/22/50. See `SEMANTIC_CATALOG_V2.md` for its source and quality
rationale.

Generated counts use an inclusive discrete uniform draw. For example, each of
20, 21, 22, 23, and 24 has equal probability in the ego and road-user layers.
The `seeds.element_count` value makes these draws reproducible.

## Running the profiles

```bash
# Meaningful, stable semantic IDs
python run_simulation.py \
  --config config_semantic_catalog_v5s.yaml \
  --outdir results_semantic_v5s

# Larger fixed and source-traceable semantic catalog v2.0
python run_simulation.py \
  --config config_semantic_catalog_v2.yaml \
  --outdir results_semantic_v2

# Anonymous generated IDs and uniformly sampled counts
python run_simulation.py \
  --config config_generated_elements_v5g.yaml \
  --outdir results_generated_v5g
```

Use separate output folders as shown above. The runner will otherwise replace
files with the same names in an existing output directory.

## Shared and different behavior

Both profiles inherit the same mileage, duration, probability, transition,
unknown-scenario, random-seed, and fixed-street settings from `config.yaml`.
The generated profile overrides only its profile identity and the construction
form of the five non-street layers.

The semantic profile supports understandable rules and repeatable analysis
because an ID keeps the same meaning between runs. In the generated profile,
an ID such as `ego_003` identifies only a generated position and has no defined
real-world meaning. Changing construction seeds can also change the number and
rarity of generated elements.

Because the two profiles use different catalog sizes, differences between
their output statistics cannot be attributed to naming alone. A controlled
experiment comparing only naming would need equal element counts and matching
rarity assignments in both profiles.

## Configuration inheritance

The profile files use an `extends` key. Paths are resolved relative to the
profile file, mappings are merged recursively, and explicit `null` values can
remove an inherited construction form. This keeps shared simulation settings
in one place while preserving two visibly distinct profile files.
