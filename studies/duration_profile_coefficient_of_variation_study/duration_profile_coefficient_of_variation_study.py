"""Sweep each rarity class's Gamma coefficient of variation."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 1, 1.25, 1.5, 2)
LEVELS = [
    level(f"{rarity}_{value:g}", value, rarity=rarity)
    for rarity in ("common", "rare", "unknown") for value in VALUES
]


def mutate(cfg, study_level):
    cfg.duration_profiles = {
        rarity: dict(profile) for rarity, profile in cfg.duration_profiles.items()
    }
    cfg.duration_profiles[study_level["rarity"]]["coefficient_of_variation"] = study_level["value"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="duration_profile_coefficient_of_variation_study",
        description="Tests duration-tail and clustering sensitivity at fixed element means.",
        levels=LEVELS, mutate=mutate,
    )
