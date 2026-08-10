"""Sweep within-class element mean spread using ten valid values."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3)
LEVELS = [level(f"spread_{value:g}", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.duration_profiles = {
        rarity: {**profile, "element_spread": study_level["value"]}
        for rarity, profile in cfg.duration_profiles.items()
    }


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="duration_profile_element_spread_study",
        description="Tests sensitivity to heterogeneity between elements in the same rarity class.",
        levels=LEVELS, mutate=mutate,
    )
