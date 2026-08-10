"""Sweep the global minimum sampled-duration clamp."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (0.001, 0.01, 0.1, 0.5, 1, 2, 5, 10, 20, 30)
LEVELS = [level(f"{value:g}_seconds", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.min_duration_seconds = float(study_level["value"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="minimum_duration_study",
        description="Tests clamp-induced duration bias, transition suppression, and episode persistence.",
        levels=LEVELS, mutate=mutate,
    )
