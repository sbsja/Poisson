# Simulator profile

The active simulator supports generated elements only.

`config.yaml` is the complete default profile.
`config_generated_elements_v5g.yaml` is a compatibility alias that extends
the same generated configuration.

Every layer samples its element count from an inclusive configured range.
`element_class_percentages` determines the integer common/rare/unknown element
counts through largest-remainder allocation. `selection_class_percentages`
sets the exact transition-probability mass assigned to each class.

Run:

```bash
python run_simulation.py --config config.yaml --outdir results
```

Semantic catalogue and fixed-element profiles are no longer supported.
