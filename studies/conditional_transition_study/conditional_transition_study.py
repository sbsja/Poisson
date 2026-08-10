"""Sweep contextual rare-selection multipliers in conditional mode."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import level, run_study  # noqa: E402

MULTIPLIERS = (0, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 4, 10, 100)
LEVELS = [level("independent", None, mode="independent")]
LEVELS.extend(level(f"conditional_x{value:g}", value, mode="conditional")
              for value in MULTIPLIERS)


def mutate(cfg, study_level):
    if study_level["mode"] == "independent":
        cfg.transition_model = {
            "mode": "independent",
            "conditional": {"apply_to_initial_state": True, "rules": []},
        }
        return
    cfg.transition_model = {
        "mode": "conditional",
        "conditional": {
            "apply_to_initial_state": True,
            "rules": [{
                "id": "rare_street_changes_ego_rarity",
                "target_layer": "ego_maneuver",
                "when": {"street": {"rarities": ["rare"]}},
                "multipliers": {"rarities": {"rare": study_level["value"]}},
            }],
        },
    }


if __name__ == "__main__":
    run_study(
        study_file=__file__, study_name="conditional_transition_study",
        description="Tests concentration of ego rare behavior when the street layer is rare.",
        levels=LEVELS, mutate=mutate,
    )
