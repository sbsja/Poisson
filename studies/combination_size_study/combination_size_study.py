"""Compare alternative allocations of rules between C3, C4, C5, and C6."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

PRESETS = (
    ("none", {3: 0, 4: 0, 5: 0, 6: 0}),
    ("c3_only_40", {3: 40, 4: 0, 5: 0, 6: 0}),
    ("c4_only_40", {3: 0, 4: 40, 5: 0, 6: 0}),
    ("c5_only_40", {3: 0, 4: 0, 5: 40, 6: 0}),
    ("c6_only_40", {3: 0, 4: 0, 5: 0, 6: 40}),
    ("c3_c4", {3: 50, 4: 50, 5: 0, 6: 0}),
    ("c4_c5", {3: 0, 4: 50, 5: 50, 6: 0}),
    ("c5_c6", {3: 0, 4: 0, 5: 50, 6: 50}),
    ("equal_25", {3: 25, 4: 25, 5: 25, 6: 25}),
    ("front_loaded", {3: 70, 4: 20, 5: 8, 6: 2}),
    ("baseline", {3: 40, 4: 30, 5: 20, 6: 10}),
    ("reverse", {3: 10, 4: 20, 5: 30, 6: 40}),
)
LEVELS = [level(name, index, counts=counts) for index, (name, counts) in enumerate(PRESETS)]


def mutate(cfg, study_level):
    cfg.unknown_scenarios = dict(cfg.unknown_scenarios)
    cfg.unknown_scenarios["combination_counts"] = dict(study_level["counts"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="combination_size_study",
        description="Isolates the strong rarity effect of requiring 3, 4, 5, or 6 rare layers.",
        levels=LEVELS, mutate=mutate,
    )
