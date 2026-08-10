"""Compare element self-transitions allowed and forbidden."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

LEVELS = [level("self_transitions_off", False), level("self_transitions_on", True)]


def mutate(cfg, study_level):
    cfg.allow_self_transition = study_level["value"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="allow_self_transition_study",
        description="Boolean structural study of forced element turnover at layer expiry.",
        levels=LEVELS, mutate=mutate,
    )
