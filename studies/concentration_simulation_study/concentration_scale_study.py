"""Current-v6 concentration-scale sensitivity study."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

VALUES = (100, 300, 1_000, 3_000, 10_000, 20_000, 50_000,
          100_000, 300_000, 1_000_000)
LEVELS = [level(f"c_{value}", value) for value in VALUES]


def mutate(cfg, study_level):
    cfg.concentration_scale = float(study_level["value"])


def main(argv=None):
    return run_study(
        study_file=__file__, study_name="concentration_scale_study",
        description=("Measures within-class probability concentration and "
                     "seed sensitivity under the v6 direct-class-mass model."),
        levels=LEVELS, mutate=mutate, argv=argv,
    )


if __name__ == "__main__":
    main()
