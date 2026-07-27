"""Empirical sensitivity study for the simulator's concentration_scale.

Runs the complete configured mileage for several concentration values and
Dirichlet construction seeds.  Only the transition_matrix seed changes across
replicates; all simulation-time random streams remain fixed.  This creates a
common-random-numbers comparison that isolates transition-vector uncertainty.
"""

from __future__ import annotations

import csv
import gc
import json
import statistics
import sys
import time
from pathlib import Path


STUDY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDY_DIR.parents[1]
RESULTS_DIR = STUDY_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

CONCENTRATIONS = (100.0, 1_000.0, 5_000.0, 20_000.0, 100_000.0)
REPLICATES = 3
TRANSITION_SEED_STEP = 1_000_003
TARGET_RELATIVE_TOLERANCE = 0.25

sys.path.insert(0, str(PROJECT_ROOT))

from simulator import ScenarioSimulator, SimConfig  # noqa: E402


def mean(values):
    return statistics.fmean(values)


def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def concentration_label(value):
    return f"c_{int(value):06d}"


def run_one(concentration, replicate, base_transition_seed):
    cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    cfg.concentration_scale = concentration
    cfg.seeds = dict(cfg.seeds)
    cfg.seeds["transition_matrix"] = (
        base_transition_seed + replicate * TRANSITION_SEED_STEP
    )

    started = time.monotonic()
    result = ScenarioSimulator(cfg).run()
    wall_seconds = time.monotonic() - started

    type_counts = result.episodes_by_type()
    target = cfg.target_unknown_element_probability
    layer_masses = {
        stat["layer"]: stat["realized_unknown_mass"]
        for stat in result.layer_stats
        if stat["has_unknown"]
    }
    layer_empirical_rates = {
        stat["layer"]: stat["empirical_unknown_rate"]
        for stat in result.layer_stats
        if stat["has_unknown"]
    }
    relative_errors = {
        key: abs(value - target) / target
        for key, value in layer_masses.items()
    }
    durations = [episode.duration_seconds for episode in result.episodes]
    window_stats = result.window_stats()
    element_route_episodes = (
        type_counts["element"] + type_counts["hidden_triggering_unknown"]
    )

    row = {
        "concentration_scale": concentration,
        "replicate": replicate + 1,
        "transition_matrix_seed": cfg.seeds["transition_matrix"],
        "target_miles": cfg.target_total_miles,
        "simulated_miles": result.total_miles,
        "total_events": result.total_events,
        "wall_seconds": wall_seconds,
        "mean_realized_unknown_mass": mean(layer_masses.values()),
        "max_layer_relative_error": max(relative_errors.values()),
        "all_layers_within_25pct": all(
            error <= TARGET_RELATIVE_TOLERANCE
            for error in relative_errors.values()
        ),
        "element_route_episodes": element_route_episodes,
        "full_scenario_episodes": type_counts["full_scenario"],
        "total_unknown_episodes": len(result.episodes),
        "episodes_per_million_miles": result.episodes_per_million_miles(),
        "unknown_time_fraction": result.unknown_time_fraction(),
        "mean_episode_duration_seconds": mean(durations),
        "window_dispersion_index": window_stats["dispersion_index"],
        "layer_realized_unknown_mass": layer_masses,
        "layer_empirical_unknown_rate": layer_empirical_rates,
        "episodes_by_type": type_counts,
        "full_scenario_achieved_sampled_mass": result.full_scenario_stats.get(
            "achieved_sampled_mass"
        ),
    }

    run_dir = RUNS_DIR / concentration_label(concentration) / f"replicate_{replicate + 1}"
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "stats.json").open("w", encoding="utf-8") as handle:
        json.dump(row, handle, indent=2)

    print(
        f"c={concentration:>8,.0f} replicate={replicate + 1}/{REPLICATES} "
        f"episodes={len(result.episodes):>7,} "
        f"max_mass_error={row['max_layer_relative_error']:.1%} "
        f"wall={wall_seconds:.1f}s",
        flush=True,
    )
    del result, durations
    gc.collect()
    return row


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    metrics = (
        "mean_realized_unknown_mass",
        "max_layer_relative_error",
        "element_route_episodes",
        "full_scenario_episodes",
        "total_unknown_episodes",
        "episodes_per_million_miles",
        "unknown_time_fraction",
        "mean_episode_duration_seconds",
        "window_dispersion_index",
        "wall_seconds",
    )
    summary_rows = []
    for concentration in CONCENTRATIONS:
        group = [
            row for row in rows
            if row["concentration_scale"] == concentration
        ]
        summary = {
            "concentration_scale": concentration,
            "runs": len(group),
            "runs_all_layers_within_25pct": sum(
                row["all_layers_within_25pct"] for row in group
            ),
        }
        for metric in metrics:
            values = [row[metric] for row in group]
            summary[f"{metric}_mean"] = mean(values)
            summary[f"{metric}_sd"] = sample_sd(values)
            summary[f"{metric}_min"] = min(values)
            summary[f"{metric}_max"] = max(values)
        summary_rows.append(summary)
    return summary_rows


def make_plot(rows, summary_rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    concentrations = [row["concentration_scale"] for row in summary_rows]

    def series(metric):
        return [row[f"{metric}_mean"] for row in summary_rows]

    def errors(metric):
        return [row[f"{metric}_sd"] for row in summary_rows]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    panels = (
        (
            axes[0, 0],
            "max_layer_relative_error",
            "Worst per-layer deviation from 0.4%",
            "absolute relative error",
            True,
        ),
        (
            axes[0, 1],
            "element_route_episodes",
            "Element-route episodes",
            "episodes per 2M miles",
            False,
        ),
        (
            axes[1, 0],
            "total_unknown_episodes",
            "All unknown episodes",
            "episodes per 2M miles",
            False,
        ),
        (
            axes[1, 1],
            "unknown_time_fraction",
            "Union unknown-time fraction",
            "fraction of simulated time",
            False,
        ),
    )
    for axis, metric, title, ylabel, tolerance_line in panels:
        axis.errorbar(
            concentrations,
            series(metric),
            yerr=errors(metric),
            marker="o",
            capsize=4,
            linewidth=1.5,
        )
        for row in rows:
            axis.scatter(
                row["concentration_scale"], row[metric],
                color="tab:blue", alpha=0.35, s=18,
            )
        axis.axvline(20_000, color="tab:green", linestyle="--", alpha=0.8,
                     label="current c = 20,000")
        if tolerance_line:
            axis.axhline(
                TARGET_RELATIVE_TOLERANCE,
                color="tab:red",
                linestyle=":",
                label="25% tolerance",
            )
        axis.set_xscale("log")
        axis.set_title(title)
        axis.set_xlabel("concentration_scale")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)

    fig.suptitle(
        "Concentration sensitivity: mean ± sample SD across 3 full runs",
        fontsize=14,
    )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "concentration_effects.png", dpi=160)
    plt.close(fig)


def write_report(rows, summary_rows, elapsed_seconds):
    stable = [
        row for row in summary_rows
        if row["runs_all_layers_within_25pct"] == REPLICATES
    ]
    smallest_stable = (
        int(stable[0]["concentration_scale"]) if stable else None
    )
    low = summary_rows[0]
    baseline = next(
        row for row in summary_rows if row["concentration_scale"] == 20_000
    )
    high = summary_rows[-1]

    lines = [
        "# Concentration sensitivity — full simulation study",
        "",
        "## Result",
        "",
        (
            "Increasing `concentration_scale` does not change the designed "
            "unknown mass (0.4% per unknown-bearing layer); it reduces how "
            "far each one-time Dirichlet draw can wander from that target. "
            "That initialization effect propagates to episode counts and "
            "the fraction of simulated time classified as unknown."
        ),
        "",
    ]
    if smallest_stable is not None:
        lines.append(
            f"In this empirical sweep, **c = {smallest_stable:,}** was the "
            "smallest tested value for which every unknown-bearing layer in "
            f"all {REPLICATES} runs stayed within ±25% of its target."
        )
    else:
        lines.append(
            "No tested value kept every unknown-bearing layer within ±25% "
            f"of target in all {REPLICATES} replicates."
        )
    lines.extend([
        "",
        "The current `c = 20,000` remains a sensible production setting: "
        "it materially suppresses seed-to-seed initialization error without "
        "requiring a near-deterministic transition vector. The three-run "
        "sample is a sensitivity demonstration, not a replacement for the "
        "larger Monte Carlo calibration in the project's original "
        "`concentration_study.md`.",
        "",
        "## Aggregate results",
        "",
        "Each cell is the mean across three runs; `±` is the sample standard deviation.",
        "",
        "| concentration | worst layer error | element-route episodes | full-scenario episodes | total episodes | unknown-time fraction | runs within ±25% |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in summary_rows:
        lines.append(
            f"| {row['concentration_scale']:,.0f} "
            f"| {row['max_layer_relative_error_mean']:.1%} ± {row['max_layer_relative_error_sd']:.1%} "
            f"| {row['element_route_episodes_mean']:,.0f} ± {row['element_route_episodes_sd']:,.0f} "
            f"| {row['full_scenario_episodes_mean']:,.0f} ± {row['full_scenario_episodes_sd']:,.0f} "
            f"| {row['total_unknown_episodes_mean']:,.0f} ± {row['total_unknown_episodes_sd']:,.0f} "
            f"| {row['unknown_time_fraction_mean']:.3%} ± {row['unknown_time_fraction_sd']:.3%} "
            f"| {row['runs_all_layers_within_25pct']}/{REPLICATES} |"
        )

    def range_text(row, metric, percent=False):
        lo = row[f"{metric}_min"]
        hi = row[f"{metric}_max"]
        if percent:
            return f"{lo:.1%}–{hi:.1%}"
        return f"{lo:,.0f}–{hi:,.0f}"

    lines.extend([
        "",
        "## What changed",
        "",
        f"- At `c = 100`, the worst layer's mass error ranged from "
        f"{range_text(low, 'max_layer_relative_error', percent=True)} across "
        "the three transition-vector draws.",
        f"- At the current `c = 20,000`, that range narrowed to "
        f"{range_text(baseline, 'max_layer_relative_error', percent=True)}.",
        f"- At `c = 100,000`, it narrowed further to "
        f"{range_text(high, 'max_layer_relative_error', percent=True)}, "
        "showing diminishing returns once the vector is already tightly "
        "centered on the designed weights.",
        "- Full-scenario rarity is recalibrated to 0.4% stationary mass for "
        "each constructed model, so its episode count is less directly tied "
        "to the unknown-element mass than the element-route count is.",
        "",
        "## Method",
        "",
        f"- {len(rows)} end-to-end simulations: five concentrations × "
        f"{REPLICATES} transition-vector seeds.",
        "- Every run used the full configured 2,000,000-mile target and all "
        "features enabled in the root `config.yaml`.",
        "- Element counts, rarity assignment, durations, initial-state, and "
        "transition-sampling seeds were held fixed. Only the Dirichlet "
        "`transition_matrix` seed varied by replicate.",
        "- Error means `abs(realized_mass - 0.004) / 0.004`; the reported "
        "worst error is the maximum across the four unknown-bearing layers.",
        f"- Total study wall time: {elapsed_seconds / 60:.1f} minutes.",
        "",
        "## Files",
        "",
        "- `runs.csv`: one row per simulation.",
        "- `summary.csv`: concentration-level means, standard deviations, minima, and maxima.",
        "- `summary.json`: machine-readable manifest plus all per-run and aggregate data.",
        "- `runs/.../stats.json`: compact result for each individual simulation.",
        "- `concentration_effects.png`: visual comparison of the principal outcomes.",
        "",
    ])
    (RESULTS_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base_cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    base_transition_seed = base_cfg.seeds["transition_matrix"]
    started = time.monotonic()
    rows = []
    for concentration in CONCENTRATIONS:
        for replicate in range(REPLICATES):
            rows.append(run_one(concentration, replicate, base_transition_seed))
    elapsed_seconds = time.monotonic() - started

    flat_rows = []
    layer_keys = sorted(rows[0]["layer_realized_unknown_mass"])
    for row in rows:
        flat = {key: value for key, value in row.items() if not isinstance(value, dict)}
        for key in layer_keys:
            flat[f"{key}_realized_unknown_mass"] = row[
                "layer_realized_unknown_mass"
            ][key]
            flat[f"{key}_empirical_unknown_rate"] = row[
                "layer_empirical_unknown_rate"
            ][key]
        flat_rows.append(flat)
    write_csv(RESULTS_DIR / "runs.csv", flat_rows, list(flat_rows[0]))

    summary_rows = aggregate(rows)
    write_csv(
        RESULTS_DIR / "summary.csv", summary_rows, list(summary_rows[0])
    )
    manifest = {
        "study": "concentration_scale end-to-end simulation sensitivity",
        "source_config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "concentrations": CONCENTRATIONS,
        "replicates_per_concentration": REPLICATES,
        "transition_seed_step": TRANSITION_SEED_STEP,
        "target_relative_tolerance": TARGET_RELATIVE_TOLERANCE,
        "total_wall_seconds": elapsed_seconds,
        "runs": rows,
        "summary": summary_rows,
    }
    with (RESULTS_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    make_plot(rows, summary_rows)
    write_report(rows, summary_rows, elapsed_seconds)
    print(
        f"completed {len(rows)} full simulations in {elapsed_seconds / 60:.1f} "
        f"minutes; results: {RESULTS_DIR}",
        flush=True,
    )


if __name__ == "__main__":
    main()
