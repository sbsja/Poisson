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
| Three rarities, per-element durations, C3-C6 unknowns, time stop | **v6** (`prompt_v6_changes.md`) | **config v6** |

- **"Config" scheme** = the chronological configuration labels used in
  `README.md` and `config.yaml`. Result folders are named with this scheme,
  because a results folder represents a *configuration*.
- **"Change-request" scheme** = the `prompt_vN_changes.md` filenames.

## Current simulator (working tree)

- Current **default `config.yaml`** = **config v6**. It uses only `common`,
  `rare`, and `unknown`; derives a separate Gamma law per element; selects
  exact C3-C6 rare-element combinations that always include a triggering
  condition; removes all earlier unknown routes; and stops exactly after
  20,000 simulated hours. Every layer is generated from a configured count
  range. Users directly configure element-class and selection-class percentages
  that each sum to 100. Semantic catalogues, fixed elements, rarity weights, and
  the analytical unknown-weight solution have been removed.
- Each run reports exact common/rare/unknown element counts and achieved
  proportions per layer and across all layers in
  both `summary.md` and `stats.json`.
- The two "v4"s are **mutually exclusive**: `mode: conditional` +
  `full_scenario_unknowns.enabled: true` is rejected
  (`prompt_v4_changes.md:98-104`). No saved results folder was produced by the
  conditional code path.

## Result folders

| Folder | Mechanism (from its `summary.md`) | Config version | Notes |
|---|---|---|---|
| `results_configv3_combos/` | hash + pattern combinations; has legacy `encounters.csv` | config v3 | Oldest saved run. Old encounter-counting schema; not valid for the current config. |
| `results_configv4_fullscenario_early/` | full-scenario rarity, 2-route (element + full-scenario), **no** hidden-triggering | config v4 (early) | Predates the three-route change; regenerate before comparing. |
| `results_configv4_fullscenario_current/` | full-scenario rarity, 3-route (element + hidden-triggering + full-scenario) | config v4 (historical) | Historical saved run; it does not match the current v6 default. |

Not versioned simulator runs:
- `studies/` — parameter-sweep studies (concentration, duration-distribution,
  window-mileage) driven by the current simulator; each has its own local
  `results/` subfolder.
- `outputs/` — PowerPoint / documentation exports, not simulation results.

## Gaps

- No saved results for config v1, config v2, or the change-request-v4
  conditional-transition path.
