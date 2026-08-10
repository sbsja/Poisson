"""Sweep each layer's baseline mean duration over ten multipliers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import CONFIG_PATH, SimConfig, level, run_study  # noqa: E402

MULTIPLIERS = (0.25, 0.4, 0.55, 0.7, 0.85, 1, 1.25, 1.5, 2, 3)
BASE = SimConfig.from_yaml(str(CONFIG_PATH))
LEVELS = [
    level(f"{layer}_x{multiplier:g}", multiplier, layer=layer,
          duration=params.mean_duration * multiplier)
    for layer, params in BASE.layers.items() for multiplier in MULTIPLIERS
]


def mutate(cfg, study_level):
    cfg.layers[study_level["layer"]].mean_duration = study_level["duration"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="layer_mean_duration_study",
        description="Measures transition-rate and persistence sensitivity to every layer time scale.",
        levels=LEVELS, mutate=mutate,
    )
