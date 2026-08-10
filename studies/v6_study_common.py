"""Shared execution and reporting framework for v6 simulator studies.

Each study supplies named levels and a mutation callback.  The framework keeps
the random streams paired across levels, varies all seven seeds between
replicates, runs the current time-based simulator, and writes a consistent set
of reproducible artifacts beneath the study's ``results`` directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable


STUDIES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDIES_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
SEED_STEP = 1_000_003
DEFAULT_REPLICATES = 3
DEFAULT_SCREENING_HOURS = 1_000.0

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator import ScenarioSimulator, SimConfig  # noqa: E402


Mutation = Callable[[SimConfig, dict[str, Any]], None]
SimulatorFactory = Callable[[SimConfig, dict[str, Any]], ScenarioSimulator]


def level(label: str, value: Any, **parameters: Any) -> dict[str, Any]:
    """Create one JSON-serializable study level."""
    return {"label": label, "value": value, **parameters}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def mean_or_none(values: Iterable[float | None]) -> float | None:
    clean = [float(value) for value in values
             if value is not None and math.isfinite(float(value))]
    return statistics.fmean(clean) if clean else None


def sd_or_none(values: Iterable[float | None]) -> float | None:
    clean = [float(value) for value in values
             if value is not None and math.isfinite(float(value))]
    return statistics.stdev(clean) if len(clean) > 1 else (0.0 if clean else None)


def config_dict(cfg: SimConfig) -> dict[str, Any]:
    data = asdict(cfg)
    data["layers"] = {key: asdict(value) for key, value in cfg.layers.items()}
    return data


def config_hash(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def offset_all_seeds(cfg: SimConfig, replicate: int) -> None:
    cfg.seeds = {
        key: int(value) + replicate * SEED_STEP
        for key, value in cfg.seeds.items()
    }


def safe_label(label_text: str) -> str:
    out = "".join(
        char.lower() if char.isalnum() else "_" for char in label_text
    ).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out or "level"


def extract_metrics(result, wall_seconds: float) -> dict[str, Any]:
    durations = [episode.duration_seconds for episode in result.episodes]
    inter_arrivals = result.inter_arrival_seconds()
    try:
        windows = result.window_stats()
    except ValueError as exc:
        # Observation-design sweeps intentionally include windows larger than
        # the generated mileage.  That configuration has no complete window;
        # it is a valid study level even though the production helper rejects
        # it for normal reporting.
        if "larger than the total mileage" not in str(exc):
            raise
        windows = {"n_windows": 0, "mean_count": None,
                   "dispersion_index": None}
    hours = result.total_time_seconds / 3600.0
    rule_masses = [
        float(rule["mass"]) for rule in result.combination_stats.get("rules", [])
    ]
    by_size = result.combination_stats.get("episodes_by_size", {})
    transitions = sum(int(row["transitions"]) for row in result.layer_stats)
    return {
        "simulated_hours": hours,
        "simulated_miles": result.total_miles,
        "total_events": result.total_events,
        "total_layer_transitions": transitions,
        "total_unknown_episodes": len(result.episodes),
        "episodes_per_hour": len(result.episodes) / hours if hours else 0.0,
        "episodes_per_million_miles": result.episodes_per_million_miles(),
        "unknown_time_fraction": result.unknown_time_fraction(),
        "episode_duration_mean_seconds": mean_or_none(durations),
        "episode_duration_median_seconds": percentile(durations, 0.50),
        "episode_duration_p90_seconds": percentile(durations, 0.90),
        "episode_duration_max_seconds": max(durations) if durations else None,
        "inter_arrival_mean_seconds": mean_or_none(inter_arrivals),
        "inter_arrival_p90_seconds": percentile(inter_arrivals, 0.90),
        "window_count": windows.get("n_windows", 0),
        "window_mean": windows.get("mean_count"),
        "dispersion_index": windows.get("dispersion_index"),
        "c3_episodes": int(by_size.get(3, by_size.get("3", 0))),
        "c4_episodes": int(by_size.get(4, by_size.get("4", 0))),
        "c5_episodes": int(by_size.get(5, by_size.get("5", 0))),
        "c6_episodes": int(by_size.get(6, by_size.get("6", 0))),
        "selected_rule_count": len(rule_masses),
        "selected_rule_mass_sum": sum(rule_masses),
        "selected_rule_mass_max": max(rule_masses) if rule_masses else 0.0,
        "wall_seconds": wall_seconds,
    }


METRICS = (
    "simulated_hours",
    "simulated_miles",
    "total_events",
    "total_layer_transitions",
    "total_unknown_episodes",
    "episodes_per_hour",
    "episodes_per_million_miles",
    "unknown_time_fraction",
    "episode_duration_mean_seconds",
    "episode_duration_median_seconds",
    "episode_duration_p90_seconds",
    "episode_duration_max_seconds",
    "inter_arrival_mean_seconds",
    "inter_arrival_p90_seconds",
    "window_count",
    "window_mean",
    "dispersion_index",
    "c3_episodes",
    "c4_episodes",
    "c5_episodes",
    "c6_episodes",
    "selected_rule_count",
    "selected_rule_mass_sum",
    "selected_rule_mass_max",
    "wall_seconds",
)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def aggregate_rows(rows: list[dict[str, Any]], levels: list[dict[str, Any]]):
    summaries = []
    for level_index, study_level in enumerate(levels):
        group = [row for row in rows if row["level_index"] == level_index]
        summary: dict[str, Any] = {
            "level_index": level_index,
            "level_label": study_level["label"],
            "level_value": study_level.get("value"),
            "runs": len(group),
        }
        for metric in METRICS:
            values = [row.get(metric) for row in group]
            clean = [float(value) for value in values
                     if value is not None and math.isfinite(float(value))]
            summary[f"{metric}_mean"] = mean_or_none(clean)
            summary[f"{metric}_sd"] = sd_or_none(clean)
            summary[f"{metric}_min"] = min(clean) if clean else None
            summary[f"{metric}_max"] = max(clean) if clean else None
        summaries.append(summary)
    return summaries


def make_plot(
    results_dir: Path,
    study_name: str,
    summaries: list[dict[str, Any]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [row["level_label"] for row in summaries]
    x = list(range(len(labels)))
    panels = (
        ("episodes_per_hour", "Unknown episode rate", "episodes/hour"),
        ("unknown_time_fraction", "Unknown occupancy", "fraction of time"),
        ("episode_duration_p90_seconds", "Episode duration p90", "seconds"),
        ("dispersion_index", "Mileage-window dispersion", "variance/mean"),
    )
    fig, axes = plt.subplots(2, 2, figsize=(max(12, len(labels) * 0.35), 8))
    for axis, (metric, title, ylabel) in zip(axes.flat, panels):
        means = [row[f"{metric}_mean"] for row in summaries]
        sds = [row[f"{metric}_sd"] for row in summaries]
        valid_x = [i for i, value in enumerate(means) if value is not None]
        valid_means = [means[i] for i in valid_x]
        valid_sds = [0.0 if sds[i] is None else sds[i] for i in valid_x]
        axis.errorbar(valid_x, valid_means, yerr=valid_sds, marker="o",
                      capsize=3, linewidth=1.2)
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    fig.suptitle(study_name.replace("_", " ").title())
    fig.tight_layout()
    fig.savefig(results_dir / f"{study_name}_effects.png", dpi=160)
    plt.close(fig)


def format_number(value: Any) -> str:
    if value is None:
        return "n/a"
    value = float(value)
    if abs(value) < 0.01 and value != 0:
        return f"{value:.4g}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def write_report(
    results_dir: Path,
    study_name: str,
    description: str,
    summaries: list[dict[str, Any]],
    replicates: int,
    screening_hours: float | None,
    elapsed: float,
) -> None:
    lines = [
        f"# {study_name.replace('_', ' ').title()}",
        "",
        description,
        "",
        "## Design",
        "",
        f"- Levels: {len(summaries)}",
        f"- Paired independent seed sets per level: {replicates}",
        "- All seven simulator seeds are shifted together between replicates.",
        "- All levels within a replicate use the same seed set.",
        (
            f"- Default screening duration: {screening_hours:g} simulated hours."
            if screening_hours is not None else
            "- Simulation duration is supplied by each study level."
        ),
        f"- Total wall time: {elapsed:.1f} seconds.",
        "",
        "## Aggregate results",
        "",
        "| level | episodes/hour | unknown-time fraction | duration p90 (s) | dispersion | C3/C4/C5/C6 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        c_values = "/".join(
            format_number(row[f"c{size}_episodes_mean"]) for size in (3, 4, 5, 6)
        )
        lines.append(
            f"| {row['level_label']} "
            f"| {format_number(row['episodes_per_hour_mean'])} "
            f"| {format_number(row['unknown_time_fraction_mean'])} "
            f"| {format_number(row['episode_duration_p90_seconds_mean'])} "
            f"| {format_number(row['dispersion_index_mean'])} "
            f"| {c_values} |"
        )
    lines.extend([
        "",
        "## Interpretation note",
        "",
        "These are screening simulations, not causal claims from a single run. "
        "Compare the level-to-level change with the replicate standard deviations "
        "in `summary.csv`; confirm influential settings with longer runs and more seeds.",
        "",
        "## Files",
        "",
        "- `baseline_config.json`: immutable source configuration snapshot.",
        "- `study_definition.json`: levels and execution settings.",
        "- `runs.csv`: one row per simulation.",
        "- `summary.csv` and `summary.json`: aggregate and machine-readable results.",
        "- `runs/<level>/replicate_<n>/config.json`: exact configuration for each run.",
        "- `runs/<level>/replicate_<n>/stats.json`: compact per-run metrics.",
        f"- `{study_name}_effects.png`: principal outcomes by level.",
        "",
    ])
    (results_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def run_study(
    *,
    study_file: str | Path,
    study_name: str,
    description: str,
    levels: list[dict[str, Any]],
    mutate: Mutation,
    default_replicates: int = DEFAULT_REPLICATES,
    screening_hours: float | None = DEFAULT_SCREENING_HOURS,
    simulator_factory: SimulatorFactory | None = None,
    argv: list[str] | None = None,
) -> dict[str, Any]:
    """Execute one study and return its summary manifest."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--replicates", type=int, default=default_replicates)
    parser.add_argument(
        "--hours", type=float, default=screening_hours,
        help="Override the default simulated hours for levels that do not mutate it.",
    )
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-run progress; still print completion.")
    parser.add_argument(
        "--quick", action="store_true",
        help="Run one replicate for 100 simulated hours for a smoke test.",
    )
    args = parser.parse_args(argv)
    if args.replicates <= 0:
        parser.error("--replicates must be positive")
    if args.hours is not None and args.hours <= 0:
        parser.error("--hours must be positive")

    replicates = 1 if args.quick else args.replicates
    effective_hours = 100.0 if args.quick else args.hours
    study_dir = Path(study_file).resolve().parent
    results_dir = study_dir / "results"
    runs_dir = results_dir / "runs"
    results_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    base_cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    base_data = config_dict(base_cfg)
    (results_dir / "baseline_config.json").write_text(
        json.dumps(base_data, indent=2), encoding="utf-8"
    )
    definition = {
        "study": study_name,
        "description": description,
        "simulator_profile": base_cfg.profile_name,
        "source_config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "levels": levels,
        "replicates": replicates,
        "seed_step": SEED_STEP,
        "screening_hours": effective_hours,
        "quick": args.quick,
    }
    (results_dir / "study_definition.json").write_text(
        json.dumps(definition, indent=2), encoding="utf-8"
    )

    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    for level_index, study_level in enumerate(levels):
        for replicate in range(replicates):
            cfg = SimConfig.from_yaml(str(CONFIG_PATH))
            cfg.target_total_miles = None
            if effective_hours is not None:
                cfg.target_total_hours = float(effective_hours)
            offset_all_seeds(cfg, replicate)
            mutate(cfg, study_level)
            cfg.validate()
            data = config_dict(cfg)
            digest = config_hash(data)

            run_started = time.monotonic()
            simulator = (
                simulator_factory(cfg, study_level)
                if simulator_factory is not None else ScenarioSimulator(cfg)
            )
            result = simulator.run()
            wall_seconds = time.monotonic() - run_started
            metrics = extract_metrics(result, wall_seconds)
            row = {
                "study": study_name,
                "level_index": level_index,
                "level_label": study_level["label"],
                "level_value": study_level.get("value"),
                "replicate": replicate + 1,
                "config_sha256": digest,
                **metrics,
            }
            rows.append(row)

            run_dir = (
                runs_dir / f"{level_index + 1:03d}_{safe_label(study_level['label'])}"
                / f"replicate_{replicate + 1}"
            )
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "config.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            (run_dir / "stats.json").write_text(
                json.dumps(row, indent=2), encoding="utf-8"
            )
            if not args.quiet:
                print(
                    f"[{study_name}] {level_index + 1}/{len(levels)} "
                    f"{study_level['label']} replicate {replicate + 1}/{replicates}: "
                    f"episodes={metrics['total_unknown_episodes']} "
                    f"rate={metrics['episodes_per_hour']:.5g}/h "
                    f"wall={wall_seconds:.2f}s",
                    flush=True,
                )

    elapsed = time.monotonic() - started
    summaries = aggregate_rows(rows, levels)
    write_csv(results_dir / "runs.csv", rows)
    write_csv(results_dir / "summary.csv", summaries)
    manifest = {
        **definition,
        "total_wall_seconds": elapsed,
        "runs": rows,
        "summary": summaries,
    }
    (results_dir / "summary.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    if not args.no_plot:
        make_plot(results_dir, study_name, summaries)
        from v6_study_charts import generate_study_charts
        generate_study_charts(results_dir, manifest)
    write_report(
        results_dir, study_name, description, summaries, replicates,
        effective_hours, elapsed,
    )
    print(
        f"[{study_name}] complete: {len(rows)} simulations in {elapsed:.1f}s; "
        f"results={results_dir}", flush=True,
    )
    return manifest
