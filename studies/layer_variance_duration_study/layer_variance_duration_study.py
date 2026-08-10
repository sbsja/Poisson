"""Sweep each layer's baseline duration variance over ten multipliers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import CONFIG_PATH, SimConfig, level, run_study  # noqa: E402

MULTIPLIERS = (0.0625, 0.125, 0.25, 0.5, 0.75, 1, 1.5, 2, 4, 8)
BASE = SimConfig.from_yaml(str(CONFIG_PATH))
LEVELS = [
    level(f"{layer}_x{multiplier:g}", multiplier, layer=layer,
          variance=params.variance_duration * multiplier)
    for layer, params in BASE.layers.items() for multiplier in MULTIPLIERS
]


def mutate(cfg, study_level):
    cfg.layers[study_level["layer"]].variance_duration = study_level["variance"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="layer_variance_duration_study",
        description="Measures tail and clustering sensitivity to every layer duration variance.",
        levels=LEVELS, mutate=mutate,
    )
