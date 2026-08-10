# Current-v6 simulation studies

The executable studies in this directory target the generated-element v6
simulator. Numeric controls have at least ten tested values wherever the
configuration permits it. Boolean controls have their two meaningful levels.

## Run everything

```powershell
& '<python.exe>' studies\run_all_studies.py --jobs 3 --quiet
```

Use `--quick --no-plot` for a 100-hour, one-seed smoke run. Every component
script also accepts `--replicates`, `--hours`, `--quiet`, and `--no-plot`.

`verify_study_results.py` confirms that the final manifests are not quick
runs, level and replicate counts are complete, and all required artifacts are
present.

## Component studies

| study | levels |
|---|---:|
| selection class percentages | 20 |
| unknown scenarios enabled | 2 (boolean) |
| combination-count scale | 10 |
| combination-size allocation | 12 |
| per-layer mean duration | 60 (10 per layer) |
| per-layer duration variance | 60 (10 per layer) |
| rarity-profile mean multiplier | 30 (10 per class) |
| rarity-profile coefficient of variation | 30 (10 per class) |
| rarity-profile element spread | 10 |
| self-transition policy | 2 (boolean) |
| concentration scale | 10 |
| exact class-mass rescaling | 2 (boolean) |
| element class percentages | 10 |
| per-layer element count | 60 (10 per layer) |
| conditional transition multiplier | 12 |
| target simulated hours | 10 |
| average speed | 10 |
| mileage-window size | 10 |
| minimum-duration clamp | 10 |
| duration-distribution family | 10 |
| whole-model seed variability | 20 |

The parameter-sensitivity study runs last. It aggregates the component
summaries and ranks their tested effect ranges against the seed-only standard
deviation.

Mechanism, exact-combination, conditional-transition, and taxonomy-to-risk
diagrams are maintained in `MODEL_DIAGRAMS.md`.

## Artifact structure

Each component study writes the following beneath its `results` directory:

- `baseline_config.json` and `study_definition.json`;
- `runs.csv`, `summary.csv`, and `summary.json`;
- `report.md` and an effects plot;
- paired-replicate, C-size, mechanism, normalized-response, and routed
  study-specific plots;
- `runs/<level>/replicate_<n>/config.json` and `stats.json`.

The exact full-suite status is recorded in `run_all_summary.json`. Older files
that are not named by the current report are retained as legacy evidence; the
current report, manifest, prefixed run directories, and specifically named v6
plot are authoritative.
