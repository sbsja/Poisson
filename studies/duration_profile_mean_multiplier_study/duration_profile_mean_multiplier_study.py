"""Sweep rarity-specific mean multipliers while preserving ordered bands."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = {
    "common": (1.0, 1.15, 1.3, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3),
    "rare": (0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.15, 1.2),
    "unknown": (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6),
}
LEVELS = [
    level(f"{rarity}_{value:g}", value, rarity=rarity)
    for rarity, values in VALUES.items() for value in values
]


def mutate(cfg, study_level):
    cfg.duration_profiles = {
        rarity: dict(profile) for rarity, profile in cfg.duration_profiles.items()
    }
    cfg.duration_profiles[study_level["rarity"]]["mean_multiplier"] = study_level["value"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="duration_profile_mean_multiplier_study",
        description="Tests how common, rare, and unknown sojourn means alter combination exposure.",
        levels=LEVELS, mutate=mutate,
    )
