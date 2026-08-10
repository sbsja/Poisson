"""Compare the v6 exact-combination mechanism enabled and disabled."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

LEVELS = [level("disabled", False), level("enabled", True)]


def mutate(cfg, study_level):
    cfg.unknown_scenarios = dict(cfg.unknown_scenarios)
    cfg.unknown_scenarios["enabled"] = study_level["value"]


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="unknown_scenarios_enabled_study",
        description="Two-level control study for the boolean v6 unknown-scenario switch.",
        levels=LEVELS, mutate=mutate,
    )
