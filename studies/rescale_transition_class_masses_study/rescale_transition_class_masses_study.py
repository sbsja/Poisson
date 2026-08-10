"""Compare exact class-mass rescaling with raw Dirichlet vectors."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

LEVELS = [level("raw_dirichlet", False), level("exact_class_masses", True)]


def mutate(cfg, study_level):
    cfg.rescale_transition_class_masses = study_level["value"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="rescale_transition_class_masses_study",
        description="Boolean study of exact versus seed-varying realized class masses.",
        levels=LEVELS, mutate=mutate,
    )
