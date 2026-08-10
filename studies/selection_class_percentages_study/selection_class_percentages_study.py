"""Sweep the direct selection probability assigned to rarity classes."""

from pathlib import Path
import sys

STUDIES_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIES_DIR))
from v6_study_common import level, run_study  # noqa: E402


LEVELS = []
for rare in (5, 10, 15, 20, 25, 30, 35, 40, 45, 50):
    LEVELS.append(level(
        f"rare_{rare:02d}pct", rare, sweep="rare",
        percentages={"common": 90.0 - rare, "rare": float(rare), "unknown": 10.0},
    ))
for unknown in (1, 3, 5, 7.5, 10, 12.5, 15, 20, 25, 30):
    LEVELS.append(level(
        f"unknown_{unknown:g}pct", unknown, sweep="unknown",
        percentages={"common": 80.0 - unknown, "rare": 20.0, "unknown": float(unknown)},
    ))


def mutate(cfg, study_level):
    cfg.selection_class_percentages = dict(study_level["percentages"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="selection_class_percentages_study",
        description=("Tests how direct common/rare/unknown transition-selection "
                     "mass changes exact rare-combination episodes."),
        levels=LEVELS, mutate=mutate,
    )
