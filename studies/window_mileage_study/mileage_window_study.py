"""Sweep mileage-window aggregation scale over ten values for current v6."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (100, 250, 500, 1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000)
LEVELS = [level(f"{value}_miles", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.mileage_window_miles = float(study_level["value"])


def main(argv=None):
    return run_study(
        study_file=__file__, study_name="mileage_window_study",
        description="Measures how reporting-window scale changes count dispersion, not state history.",
        levels=LEVELS, mutate=mutate, screening_hours=2_000.0, argv=argv,
    )


if __name__ == "__main__":
    main()
