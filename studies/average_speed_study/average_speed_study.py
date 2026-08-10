"""Sweep the time-to-mileage conversion speed over ten values."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (5, 10, 20, 30, 40, 50, 60, 75, 100, 150)
LEVELS = [level(f"{value}_mph", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.average_speed_mph = float(study_level["value"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="average_speed_study",
        description="Verifies that speed changes mileage-domain metrics but not time-domain dynamics.",
        levels=LEVELS, mutate=mutate,
    )
