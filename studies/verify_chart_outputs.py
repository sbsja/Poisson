"""Verify universal simulator and study-specific chart artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from run_all_studies import STUDIES_DIR, STUDY_FILES


PROJECT_ROOT = STUDIES_DIR.parent
BASELINE_PLOTS = (
    "cumulative_episodes.png",
    "episode_durations.png",
    "inter_arrival_hist.png",
    "window_counts.png",
    "per_layer_stats.png",
    "street_composition.png",
    "unknown_occupancy_convergence.png",
    "episode_duration_survival.png",
    "inter_arrival_diagnostics.png",
    "combination_size_contribution.png",
    "rule_contributions.png",
    "class_mass_verification.png",
    "episode_timeline.png",
)
UNIVERSAL_STUDY_PLOTS = (
    "paired_replicate_responses.png",
    "c_size_composition.png",
    "mechanism_relationships.png",
    "normalized_response_heatmap.png",
)


def main():
    failures = []
    baseline_dir = PROJECT_ROOT / "version 6" / "plots"
    for filename in BASELINE_PLOTS:
        if not (baseline_dir / filename).exists():
            failures.append(f"baseline missing {filename}")

    studies = []
    for relative in STUDY_FILES:
        results_dir = (STUDIES_DIR / relative).parent / "results"
        missing = [filename for filename in UNIVERSAL_STUDY_PLOTS
                   if not (results_dir / filename).exists()]
        if missing:
            failures.append(f"{Path(relative).parent.name}: missing {missing}")
        pngs = sorted(path.name for path in results_dir.glob("*.png"))
        studies.append({
            "study": Path(relative).parent.name,
            "chart_count": len(pngs),
            "charts": pngs,
        })

    sensitivity_dir = STUDIES_DIR / "parameter_sensitivity_study" / "results"
    sensitivity = (
        "sensitivity_tornado.png", "sensitivity_metric_heatmap.png",
        "effect_noise_scatter.png",
    )
    for filename in sensitivity:
        if not (sensitivity_dir / filename).exists():
            failures.append(f"parameter sensitivity missing {filename}")
    if not (STUDIES_DIR / "MODEL_DIAGRAMS.md").exists():
        failures.append("MODEL_DIAGRAMS.md is missing")

    payload = {
        "complete": not failures,
        "baseline_chart_count": len(BASELINE_PLOTS),
        "baseline_charts": list(BASELINE_PLOTS),
        "component_study_chart_count": sum(row["chart_count"] for row in studies),
        "studies": studies,
        "sensitivity_charts": list(sensitivity),
        "failures": failures,
    }
    (STUDIES_DIR / "chart_output_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"Verified {len(BASELINE_PLOTS)} baseline charts, "
        f"{payload['component_study_chart_count']} component-study PNGs, "
        "and 3 sensitivity charts."
    )


if __name__ == "__main__":
    main()
