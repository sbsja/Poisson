"""Negative-control study across twenty independent whole-model seed sets."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import SEED_STEP, level, run_study  # noqa: E402

LEVELS = [level(f"seed_set_{index + 1:02d}", index, offset=index * SEED_STEP)
          for index in range(20)]


def mutate(cfg, study_level):
    cfg.seeds = {key: value + study_level["offset"]
                 for key, value in cfg.seeds.items()}


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="seed_variability_study",
        description="Quantifies natural run-to-run variability with no behavioral parameter change.",
        levels=LEVELS, mutate=mutate, default_replicates=1,
    )
