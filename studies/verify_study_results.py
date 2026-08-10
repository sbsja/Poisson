"""Verify that every current-v6 study completed and produced its artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from run_all_studies import STUDIES_DIR, STUDY_FILES


BOOLEAN_STUDIES = {
    "unknown_scenarios_enabled_study",
    "allow_self_transition_study",
    "rescale_transition_class_masses_study",
}


def main():
    records = []
    failures = []
    total_simulations = 0
    for relative in STUDY_FILES:
        script = STUDIES_DIR / relative
        results = script.parent / "results"
        summary_path = results / "summary.json"
        if not summary_path.exists():
            failures.append(f"missing summary: {summary_path}")
            continue
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        name = data["study"]
        levels = len(data["levels"])
        replicates = int(data["replicates"])
        expected_runs = levels * replicates
        actual_runs = len(data["runs"])
        if data.get("quick"):
            failures.append(f"{name}: final manifest is still marked quick")
        if actual_runs != expected_runs:
            failures.append(
                f"{name}: expected {expected_runs} runs, found {actual_runs}"
            )
        if name not in BOOLEAN_STUDIES and levels < 10:
            failures.append(f"{name}: only {levels} levels (expected at least 10)")
        required = (
            "baseline_config.json", "study_definition.json", "runs.csv",
            "summary.csv", "summary.json", "report.md",
            f"{name}_effects.png",
        )
        missing = [filename for filename in required
                   if not (results / filename).exists()]
        if missing:
            failures.append(f"{name}: missing artifacts {missing}")
        total_simulations += actual_runs
        records.append({
            "study": name,
            "script": relative,
            "levels": levels,
            "replicates": replicates,
            "simulations": actual_runs,
            "total_wall_seconds": data.get("total_wall_seconds"),
            "artifacts_complete": not missing,
        })

    sensitivity = (
        STUDIES_DIR / "parameter_sensitivity_study" / "results" / "summary.json"
    )
    if not sensitivity.exists():
        failures.append("parameter_sensitivity_study summary is missing")
    payload = {
        "completed": not failures,
        "component_studies": len(records),
        "total_simulations": total_simulations,
        "studies": records,
        "failures": failures,
    }
    (STUDIES_DIR / "run_all_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"Verified {len(records)} studies, {total_simulations} simulations, "
        "and all required artifacts."
    )


if __name__ == "__main__":
    main()
