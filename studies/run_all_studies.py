"""Run every executable current-v6 simulator study in dependency order."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path


STUDIES_DIR = Path(__file__).resolve().parent
STUDY_FILES = (
    "selection_class_percentages_study/selection_class_percentages_study.py",
    "unknown_scenarios_enabled_study/unknown_scenarios_enabled_study.py",
    "combination_counts_study/combination_counts_study.py",
    "combination_size_study/combination_size_study.py",
    "layer_mean_duration_study/layer_mean_duration_study.py",
    "layer_variance_duration_study/layer_variance_duration_study.py",
    "duration_profile_mean_multiplier_study/duration_profile_mean_multiplier_study.py",
    "duration_profile_coefficient_of_variation_study/duration_profile_coefficient_of_variation_study.py",
    "duration_profile_element_spread_study/duration_profile_element_spread_study.py",
    "allow_self_transition_study/allow_self_transition_study.py",
    "concentration_simulation_study/concentration_scale_study.py",
    "rescale_transition_class_masses_study/rescale_transition_class_masses_study.py",
    "element_class_percentages_study/element_class_percentages_study.py",
    "layer_element_count_study/layer_element_count_study.py",
    "conditional_transition_study/conditional_transition_study.py",
    "target_total_hours_study/target_total_hours_study.py",
    "average_speed_study/average_speed_study.py",
    "window_mileage_study/mileage_window_study.py",
    "minimum_duration_study/minimum_duration_study.py",
    "duration_distribution_study/duration_distribution_study.py",
    "seed_variability_study/seed_variability_study.py",
)
AGGREGATOR = "parameter_sensitivity_study/parameter_sensitivity_study.py"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--replicates", type=int, default=None)
    parser.add_argument("--hours", type=float, default=None)
    parser.add_argument("--jobs", type=int, default=1,
                        help="Number of independent study processes to run concurrently.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress component per-run progress.")
    parser.add_argument("--from-study", default=None,
                        help="Resume at this script stem or study directory name.")
    args = parser.parse_args(argv)
    started = time.monotonic()
    if args.jobs <= 0:
        parser.error("--jobs must be positive")
    records = []
    active = args.from_study is None
    selected = []
    for relative in STUDY_FILES:
        path = STUDIES_DIR / relative
        if not active:
            active = args.from_study in (path.stem, path.parent.name)
            if not active:
                continue
        command = [sys.executable, str(path)]
        if args.quick:
            command.append("--quick")
        if args.no_plot:
            command.append("--no-plot")
        if args.quiet:
            command.append("--quiet")
        if args.replicates is not None:
            command.extend(["--replicates", str(args.replicates)])
        if args.hours is not None:
            command.extend(["--hours", str(args.hours)])
        selected.append((relative, command))

    def execute(item):
        relative, command = item
        print(f"\n=== Running {relative} ===", flush=True)
        run_started = time.monotonic()
        completed = subprocess.run(command, cwd=STUDIES_DIR.parent, check=False)
        return {
            "study_file": relative,
            "return_code": completed.returncode,
            "wall_seconds": time.monotonic() - run_started,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(execute, item) for item in selected]
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            records.append(record)
            if record["return_code"] != 0:
                raise SystemExit(
                    f"Study failed with exit code {record['return_code']}: "
                    f"{record['study_file']}"
                )

    aggregator_path = STUDIES_DIR / AGGREGATOR
    print(f"\n=== Running {AGGREGATOR} ===", flush=True)
    completed = subprocess.run(
        [sys.executable, str(aggregator_path)], cwd=STUDIES_DIR.parent, check=False
    )
    records.append({
        "study_file": AGGREGATOR,
        "return_code": completed.returncode,
        "wall_seconds": time.monotonic() - started,
    })
    if completed.returncode != 0:
        raise SystemExit(f"Aggregator failed with exit code {completed.returncode}")

    manifest = {
        "completed": True,
        "quick": args.quick,
        "total_wall_seconds": time.monotonic() - started,
        "studies": records,
    }
    (STUDIES_DIR / "run_all_summary.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"\nAll {len(records)} study steps completed in "
        f"{manifest['total_wall_seconds'] / 60:.1f} minutes.", flush=True,
    )


if __name__ == "__main__":
    main()
