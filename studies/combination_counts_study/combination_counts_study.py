"""Sweep the number of selected C3-C6 exact rare-element rules."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

BASE = {3: 40, 4: 30, 5: 20, 6: 10}
SCALES = (0, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5)
LEVELS = [
    level(
        f"scale_{scale:g}", scale,
        counts={size: int(round(count * scale)) for size, count in BASE.items()},
    )
    for scale in SCALES
]


def mutate(cfg, study_level):
    cfg.unknown_scenarios = dict(cfg.unknown_scenarios)
    cfg.unknown_scenarios["combination_counts"] = dict(study_level["counts"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="combination_counts_study",
        description="Measures how total selected-rule coverage affects episode frequency.",
        levels=LEVELS, mutate=mutate,
    )
