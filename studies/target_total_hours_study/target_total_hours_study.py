"""Sweep observation duration over ten time-based stopping targets."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (50, 100, 250, 500, 1_000, 2_000, 5_000, 10_000, 15_000, 20_000)
LEVELS = [level(f"{value}_hours", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.target_total_miles = None
    cfg.target_total_hours = float(study_level["value"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="target_total_hours_study",
        description="Measures convergence and uncertainty as simulated observation time increases.",
        levels=LEVELS, mutate=mutate, screening_hours=None,
    )
