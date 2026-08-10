"""Sweep the generated catalogue's rare-element share over ten levels."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

# Six percent is the lowest feasible share for the baseline catalogue sizes:
# at 5%, only eight distinct C6 candidates exist while v6 requests ten rules.
RARE_VALUES = (6, 8, 10, 15, 20, 25, 30, 35, 40, 50)
LEVELS = [
    level(f"rare_elements_{rare}pct", rare,
          percentages={"common": 90.0 - rare, "rare": float(rare), "unknown": 10.0})
    for rare in RARE_VALUES
]


def mutate(cfg, study_level):
    cfg.element_class_percentages = dict(study_level["percentages"])


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="element_class_percentages_study",
        description="Tests dilution and catalogue-composition effects at fixed class selection mass.",
        levels=LEVELS, mutate=mutate,
    )
