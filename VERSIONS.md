# Simulator versions & result-folder mapping

This repo uses **two** version-numbering schemes that are offset by one. This
file is the authoritative reconciliation. See also `prompt_v3_changes.md:6-9`,
which first documented the offset.

## The two schemes

| Mechanism | Change-request doc (`prompt_vN_changes.md`) | README/config "configuration" # |
|---|---|---|
| Original assignment (specified in chat) | v1 | v1 |
| Episode semantics, fixed street layer, concentration study | v2 | v2 |
| Hash + pattern combinations re-enabled | v2 §8 addendum | **config v3** |
| Full-scenario rarity unknowns | **v3** (`prompt_v3_changes.md`) | **config v4** |
| Conditional transition model between layers | **v4** (`prompt_v4_changes.md`) | *(no config number assigned)* |
| Fixed semantic element catalogs | **v5** (`prompt_v5_changes.md`) | **config v5** |

- **"Config" scheme** = the chronological configuration labels used in
  `README.md` and `config.yaml`. Result folders are named with this scheme,
  because a results folder represents a *configuration*.
- **"Change-request" scheme** = the `prompt_vN_changes.md` filenames.

## Current simulator (working tree)

- Code implements the **change-request v5** semantic-catalog feature while
  retaining the v4 conditional transition model.
- Current **default `config.yaml`** = **config v5 semantic catalogs** with the
  config-v4 full-scenario three-route mechanism retained:
  `transition_model.mode: independent` (the conditional feature is present but
  **dormant**), hash/pattern combinations off, `hidden_triggering: true`,
  `full_scenario_unknowns.enabled: true`. Every non-street layer uses semantic
  catalog version `1.0`.
- Two named comparison profiles sit on top of that implementation: **v5-S**
  (`config_semantic_catalog_v5s.yaml`) retains stable semantic IDs, while
  **v5-G** (`config_generated_elements_v5g.yaml`) uses anonymous generated IDs
  and uniformly sampled element counts. These suffixes identify profile type,
  not a later change-request version. See `SIMULATOR_PROFILES.md`.
- `config_semantic_catalog_v2.yaml` adds a separate high-quality semantic
  catalog version `2.0` with fixed source-traceable counts. It does not replace
  the v1.0 profile. See `SEMANTIC_CATALOG_V2.md`.
- The two "v4"s are **mutually exclusive**: `mode: conditional` +
  `full_scenario_unknowns.enabled: true` is rejected
  (`prompt_v4_changes.md:98-104`). No saved results folder was produced by the
  conditional code path.

## Result folders

| Folder | Mechanism (from its `summary.md`) | Config version | Notes |
|---|---|---|---|
| `results_configv3_combos/` | hash + pattern combinations; has legacy `encounters.csv` | config v3 | Oldest saved run. Old encounter-counting schema; not valid for the current config. |
| `results_configv4_fullscenario_early/` | full-scenario rarity, 2-route (element + full-scenario), **no** hidden-triggering | config v4 (early) | Predates the three-route change; regenerate before comparing. |
| `results_configv4_fullscenario_current/` | full-scenario rarity, 3-route (element + hidden-triggering + full-scenario) | config v4 (current) | Latest saved full run; matches the current default `config.yaml`. |

Not versioned simulator runs:
- `studies/` — parameter-sweep studies (concentration, duration-distribution,
  window-mileage) driven by the current simulator; each has its own local
  `results/` subfolder.
- `outputs/` — PowerPoint / documentation exports, not simulation results.

## Gaps

- No saved results for config v1, config v2, or the change-request-v4
  conditional-transition path.
