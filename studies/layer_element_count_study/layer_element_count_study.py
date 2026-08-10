"""Pin every layer to ten different generated element counts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import CONFIG_PATH, SimConfig, level, run_study  # noqa: E402

BASE = SimConfig.from_yaml(str(CONFIG_PATH))
MULTIPLIERS = (0.5, 0.625, 0.75, 0.875, 1, 1.125, 1.25, 1.375, 1.5, 1.625)
LEVELS = []
for layer, params in BASE.layers.items():
    center = (params.element_count_min + params.element_count_max) / 2.0
    counts = []
    for multiplier in MULTIPLIERS:
        candidate = max(6, int(round(center * multiplier)))
        while candidate in counts:
            candidate += 1
        counts.append(candidate)
    LEVELS.extend(
        level(f"{layer}_n{count}", count, layer=layer)
        for count in counts
    )


def mutate(cfg, study_level):
    params = cfg.layers[study_level["layer"]]
    params.element_count_min = int(study_level["value"])
    params.element_count_max = int(study_level["value"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="layer_element_count_study",
        description="Measures per-element probability dilution as each layer catalogue changes size.",
        levels=LEVELS, mutate=mutate,
    )
