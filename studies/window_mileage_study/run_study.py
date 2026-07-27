"""Study simulation mileage and episode-count window-size choices.

Five independent 2M-mile histories are simulated.  Shorter mileage choices
are evaluated as prefixes of those histories, and window statistics are
recomputed from episode starts.  This avoids introducing unrelated randomness
when comparing mileage totals and avoids rerunning a simulation for a setting
that affects reporting only.
"""

from __future__ import annotations

import bisect
import csv
import gc
import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np


STUDY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDY_DIR.parents[1]
RESULTS_DIR = STUDY_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

MILEAGE_LEVELS = (100_000.0, 200_000.0, 500_000.0, 1_000_000.0, 2_000_000.0)
WINDOW_SIZES = (1_000.0, 5_000.0, 10_000.0, 25_000.0, 50_000.0, 100_000.0)
REPLICATES = 5
RUNTIME_SEED_STEP = 1_000_003
RUNTIME_SEED_KEYS = ("duration", "initial_state", "transition_sampling")
DEFAULT_WINDOW = 10_000.0
MIN_WINDOWS_FOR_RELIABLE_DISPERSION = 30

sys.path.insert(0, str(PROJECT_ROOT))

from simulator import ScenarioSimulator, SimConfig  # noqa: E402


def mean(values):
    return statistics.fmean(values)


def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def coefficient_of_variation(values):
    value_mean = mean(values)
    return sample_sd(values) / value_mean if value_mean else None


def union_time_until(episodes, end_time_seconds):
    """Union of episode intervals clipped at a prefix boundary."""
    total = 0.0
    merged_start = None
    merged_end = None
    for episode in episodes:
        if episode.start_time_seconds >= end_time_seconds:
            break
        start = episode.start_time_seconds
        end = min(episode.end_time_seconds, end_time_seconds)
        if end <= start:
            continue
        if merged_start is None:
            merged_start, merged_end = start, end
        elif start <= merged_end:
            merged_end = max(merged_end, end)
        else:
            total += merged_end - merged_start
            merged_start, merged_end = start, end
    if merged_start is not None:
        total += merged_end - merged_start
    return total


def window_statistics(start_miles, total_miles, window_miles):
    """Statistics over complete fixed windows; dispersion needs >=2 windows."""
    n_windows = int(total_miles // window_miles)
    if n_windows < 1:
        return None
    covered_miles = n_windows * window_miles
    stop = bisect.bisect_left(start_miles, covered_miles)
    counts = [0] * n_windows
    for position in start_miles[:stop]:
        index = min(int(position // window_miles), n_windows - 1)
        counts[index] += 1
    mean_count = mean(counts)
    if n_windows >= 2:
        variance_count = statistics.variance(counts)
        dispersion = variance_count / mean_count if mean_count else None
        count_cv = math.sqrt(variance_count) / mean_count if mean_count else None
    else:
        variance_count = None
        dispersion = None
        count_cv = None
    return {
        "window_miles": window_miles,
        "n_windows": n_windows,
        "covered_miles": covered_miles,
        "episodes_in_complete_windows": sum(counts),
        "mean_count": mean_count,
        "variance_count": variance_count,
        "dispersion_index": dispersion,
        "window_count_cv": count_cv,
    }


def prefix_metrics(result, replicate, total_miles):
    speed = result.config.average_speed_mph
    end_time = total_miles / speed * 3600.0
    start_miles = [episode.start_mileage for episode in result.episodes]
    stop = bisect.bisect_left(start_miles, total_miles)
    prefix_episodes = result.episodes[:stop]
    type_counts = Counter(episode.type for episode in prefix_episodes)
    union_seconds = union_time_until(result.episodes, end_time)
    default_windows = window_statistics(start_miles, total_miles, DEFAULT_WINDOW)
    return {
        "replicate": replicate + 1,
        "total_miles": total_miles,
        "simulated_time_seconds": end_time,
        "total_unknown_episodes": len(prefix_episodes),
        "episodes_per_million_miles": len(prefix_episodes) / (total_miles / 1e6),
        "element_episodes": type_counts["element"],
        "hidden_triggering_episodes": type_counts["hidden_triggering_unknown"],
        "full_scenario_episodes": type_counts["full_scenario"],
        "unknown_union_time_seconds": union_seconds,
        "unknown_time_fraction": union_seconds / end_time,
        "default_window_miles": DEFAULT_WINDOW,
        "default_window_count": default_windows["n_windows"],
        "default_window_mean_count": default_windows["mean_count"],
        "default_window_dispersion": default_windows["dispersion_index"],
    }, start_miles


def run_one(replicate):
    cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    cfg.target_total_miles = max(MILEAGE_LEVELS)
    cfg.seeds = dict(cfg.seeds)
    for key in RUNTIME_SEED_KEYS:
        cfg.seeds[key] += replicate * RUNTIME_SEED_STEP
    started = time.monotonic()
    result = ScenarioSimulator(cfg).run()
    wall_seconds = time.monotonic() - started

    mileage_rows = []
    window_rows = []
    start_miles = None
    for total_miles in MILEAGE_LEVELS:
        mileage_row, start_miles = prefix_metrics(result, replicate, total_miles)
        mileage_rows.append(mileage_row)
        for window_miles in WINDOW_SIZES:
            stats_row = window_statistics(start_miles, total_miles, window_miles)
            if stats_row is None:
                continue
            stats_row.update({
                "replicate": replicate + 1,
                "total_miles": total_miles,
                "enough_windows_for_reliable_dispersion": (
                    stats_row["n_windows"] >= MIN_WINDOWS_FOR_RELIABLE_DISPERSION
                ),
            })
            window_rows.append(stats_row)

    full_row = mileage_rows[-1]
    for row in mileage_rows:
        row["episode_rate_abs_pct_error_vs_2m"] = abs(
            row["episodes_per_million_miles"]
            - full_row["episodes_per_million_miles"]
        ) / full_row["episodes_per_million_miles"]
        row["unknown_fraction_abs_percentage_point_error_vs_2m"] = abs(
            row["unknown_time_fraction"] - full_row["unknown_time_fraction"]
        ) * 100.0

    run_record = {
        "replicate": replicate + 1,
        "runtime_seeds": {key: cfg.seeds[key] for key in RUNTIME_SEED_KEYS},
        "wall_seconds": wall_seconds,
        "simulated_miles": result.total_miles,
        "total_events": result.total_events,
        "total_unknown_episodes": len(result.episodes),
        "mileage_results": mileage_rows,
        "window_results": window_rows,
    }
    run_dir = RUNS_DIR / f"replicate_{replicate + 1}"
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "stats.json").open("w", encoding="utf-8") as handle:
        json.dump(run_record, handle, indent=2)
    print(
        f"replicate={replicate + 1}/{REPLICATES} "
        f"episodes={len(result.episodes):>7,} "
        f"rate={full_row['episodes_per_million_miles']:>8,.1f}/Mmi "
        f"unknown_time={full_row['unknown_time_fraction']:.3%} "
        f"wall={wall_seconds:.1f}s",
        flush=True,
    )
    del result, start_miles
    gc.collect()
    return run_record, mileage_rows, window_rows


def aggregate_mileage(rows):
    metrics = (
        "total_unknown_episodes",
        "episodes_per_million_miles",
        "element_episodes",
        "hidden_triggering_episodes",
        "full_scenario_episodes",
        "unknown_time_fraction",
        "default_window_mean_count",
        "default_window_dispersion",
        "episode_rate_abs_pct_error_vs_2m",
        "unknown_fraction_abs_percentage_point_error_vs_2m",
    )
    output = []
    for total_miles in MILEAGE_LEVELS:
        group = [row for row in rows if row["total_miles"] == total_miles]
        summary = {
            "total_miles": total_miles,
            "runs": len(group),
            "default_window_miles": DEFAULT_WINDOW,
            "default_window_count": int(total_miles // DEFAULT_WINDOW),
        }
        for metric in metrics:
            values = [row[metric] for row in group]
            summary[f"{metric}_mean"] = mean(values)
            summary[f"{metric}_sd"] = sample_sd(values)
            summary[f"{metric}_min"] = min(values)
            summary[f"{metric}_max"] = max(values)
        summary["episodes_per_million_miles_cv"] = coefficient_of_variation(
            [row["episodes_per_million_miles"] for row in group]
        )
        summary["unknown_time_fraction_cv"] = coefficient_of_variation(
            [row["unknown_time_fraction"] for row in group]
        )
        output.append(summary)
    return output


def aggregate_windows(rows):
    metrics = (
        "mean_count",
        "variance_count",
        "dispersion_index",
        "window_count_cv",
    )
    output = []
    for total_miles in MILEAGE_LEVELS:
        for window_miles in WINDOW_SIZES:
            group = [
                row for row in rows
                if row["total_miles"] == total_miles
                and row["window_miles"] == window_miles
            ]
            if not group:
                continue
            summary = {
                "total_miles": total_miles,
                "window_miles": window_miles,
                "runs": len(group),
                "n_windows": group[0]["n_windows"],
                "covered_miles": group[0]["covered_miles"],
                "enough_windows_for_reliable_dispersion": group[0][
                    "enough_windows_for_reliable_dispersion"
                ],
            }
            for metric in metrics:
                values = [row[metric] for row in group if row[metric] is not None]
                if values:
                    summary[f"{metric}_mean"] = mean(values)
                    summary[f"{metric}_sd"] = sample_sd(values)
                    summary[f"{metric}_min"] = min(values)
                    summary[f"{metric}_max"] = max(values)
                else:
                    summary[f"{metric}_mean"] = None
                    summary[f"{metric}_sd"] = None
                    summary[f"{metric}_min"] = None
                    summary[f"{metric}_max"] = None
            dispersion_values = [
                row["dispersion_index"] for row in group
                if row["dispersion_index"] is not None
            ]
            summary["dispersion_across_run_cv"] = (
                coefficient_of_variation(dispersion_values)
                if dispersion_values else None
            )
            output.append(summary)
    return output


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_plots(mileage_summary, window_summary):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    miles = np.asarray([row["total_miles"] for row in mileage_summary])

    axes[0, 0].errorbar(
        miles,
        [row["episodes_per_million_miles_mean"] for row in mileage_summary],
        yerr=[row["episodes_per_million_miles_sd"] for row in mileage_summary],
        marker="o", capsize=4,
    )
    axes[0, 0].set_title("Episode-rate convergence")
    axes[0, 0].set_xlabel("simulated miles")
    axes[0, 0].set_ylabel("episodes per million miles")

    axes[0, 1].errorbar(
        miles,
        [row["unknown_time_fraction_mean"] for row in mileage_summary],
        yerr=[row["unknown_time_fraction_sd"] for row in mileage_summary],
        marker="o", capsize=4, color="tab:orange",
    )
    axes[0, 1].set_title("Unknown-time fraction convergence")
    axes[0, 1].set_xlabel("simulated miles")
    axes[0, 1].set_ylabel("fraction of simulated time")

    for total_miles in MILEAGE_LEVELS:
        group = [
            row for row in window_summary
            if row["total_miles"] == total_miles
            and row["dispersion_index_mean"] is not None
        ]
        axes[1, 0].plot(
            [row["window_miles"] for row in group],
            [row["dispersion_index_mean"] for row in group],
            marker="o", label=f"{total_miles / 1e6:g}M mi",
        )
    axes[1, 0].axvline(
        DEFAULT_WINDOW, color="black", linestyle="--", alpha=0.65,
        label="current 10k",
    )
    axes[1, 0].set_title("Measured dispersion changes with window scale")
    axes[1, 0].set_xlabel("window size (miles)")
    axes[1, 0].set_ylabel("variance / mean")
    axes[1, 0].set_xscale("log")
    axes[1, 0].legend(fontsize=8, ncol=2)

    full_group = [
        row for row in window_summary
        if row["total_miles"] == max(MILEAGE_LEVELS)
        and row["dispersion_across_run_cv"] is not None
    ]
    x = np.arange(len(full_group))
    axes[1, 1].bar(
        x,
        [row["dispersion_across_run_cv"] for row in full_group],
        color=[
            "tab:blue" if row["window_miles"] == DEFAULT_WINDOW else "tab:gray"
            for row in full_group
        ],
    )
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(
        [f"{row['window_miles'] / 1000:g}k" for row in full_group]
    )
    axes[1, 1].set_title("Dispersion uncertainty across 2M-mile runs")
    axes[1, 1].set_xlabel("window size")
    axes[1, 1].set_ylabel("across-run coefficient of variation")

    for axis in axes.flat:
        axis.grid(alpha=0.25)
        if axis in (axes[0, 0], axes[0, 1]):
            axis.set_xscale("log")
            axis.ticklabel_format(axis="y", style="plain", useOffset=False)
    fig.suptitle(
        "Window-size and total-mileage sensitivity\n"
        "mean ± sample SD across 5 independent histories",
        fontsize=14,
    )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "window_mileage_effects.png", dpi=160)
    plt.close(fig)


def write_report(mileage_summary, window_summary, elapsed_seconds):
    precision_candidates = [
        row for row in mileage_summary
        if row["episode_rate_abs_pct_error_vs_2m_mean"] <= 0.02
        and row[
            "unknown_fraction_abs_percentage_point_error_vs_2m_mean"
        ] <= 0.10
        and row["default_window_count"] >= MIN_WINDOWS_FOR_RELIABLE_DISPERSION
    ]
    precision_miles = (
        precision_candidates[0]["total_miles"] if precision_candidates else None
    )
    full_miles = max(MILEAGE_LEVELS)
    default_full = next(
        row for row in window_summary
        if row["total_miles"] == full_miles
        and row["window_miles"] == DEFAULT_WINDOW
    )
    largest_full = next(
        row for row in window_summary
        if row["total_miles"] == full_miles
        and row["window_miles"] == max(WINDOW_SIZES)
    )

    lines = [
        "# Window-size and total-mileage study",
        "",
        "## Outcome",
        "",
        "The two settings affect different things:",
        "",
        "- **Total simulated miles affects statistical stability.** Short runs "
        "produce valid results, but episode rates, unknown-time fractions, and "
        "dispersion estimates vary more between random histories.",
        "- **Window size does not change the simulation outcome.** It changes "
        "how episode starts are grouped, so it changes the measured dispersion "
        "and the number of independent windows available for estimating it.",
        "",
    ]
    if precision_miles is not None:
        lines.append(
            f"Using the explicit study rule—mean rate error no more than 2% "
            f"from the same run's 2M-mile result, unknown-time error no more "
            f"than 0.10 percentage point, and at least "
            f"{MIN_WINDOWS_FOR_RELIABLE_DISPERSION} default windows—the "
            f"smallest tested distance that passed was **{precision_miles:,.0f} miles**."
        )
    lines.extend([
        "",
        f"At 2M miles, the current 10,000-mile window supplies "
        f"{default_full['n_windows']} windows and measured dispersion "
        f"{default_full['dispersion_index_mean']:.2f} ± "
        f"{default_full['dispersion_index_sd']:.2f}. A 100,000-mile window "
        f"supplies only {largest_full['n_windows']} windows. Its observed "
        f"across-run variation was {largest_full['dispersion_across_run_cv']:.1%}, "
        "but 20 observations remain too few for a robust variance estimate.",
        "",
        "In these five full histories, the 1,000- and 5,000-mile windows "
        "produced the most repeatable dispersion estimates. The current "
        "10,000-mile window remains a practical balance: 200 observations, "
        "hundreds of episodes per window, and less granular reporting than "
        "the smaller alternatives.",
        "",
        "**Recommendation:** keep the existing 2,000,000-mile target and "
        "10,000-mile window for final reporting. For exploratory runs, use at "
        "least the precision distance identified above. Keep at least 30 "
        "complete windows when interpreting dispersion; for short runs, reduce "
        "window size rather than accepting only a handful of windows.",
        "",
        "## Effect of total mileage",
        "",
        "Each cell is the mean across five histories; `±` is sample standard deviation.",
        "",
        "| simulated miles | episodes | episodes/M mile | rate error vs 2M | unknown-time fraction | unknown-time error | 10k windows | 10k dispersion |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in mileage_summary:
        lines.append(
            f"| {row['total_miles']:,.0f} "
            f"| {row['total_unknown_episodes_mean']:,.0f} ± {row['total_unknown_episodes_sd']:,.0f} "
            f"| {row['episodes_per_million_miles_mean']:,.0f} ± {row['episodes_per_million_miles_sd']:,.0f} "
            f"| {row['episode_rate_abs_pct_error_vs_2m_mean']:.2%} "
            f"| {row['unknown_time_fraction_mean']:.3%} ± {row['unknown_time_fraction_sd']:.3%} "
            f"| {row['unknown_fraction_abs_percentage_point_error_vs_2m_mean']:.3f} pp "
            f"| {row['default_window_count']} "
            f"| {row['default_window_dispersion_mean']:.2f} ± {row['default_window_dispersion_sd']:.2f} |"
        )

    lines.extend([
        "",
        "## Effect of window size at 2M miles",
        "",
        "| window size | complete windows | mean episodes/window | dispersion | dispersion variation across runs | enough windows? |",
        "|---:|---:|---:|---:|---:|---:|",
    ])
    for row in window_summary:
        if row["total_miles"] != full_miles:
            continue
        lines.append(
            f"| {row['window_miles']:,.0f} "
            f"| {row['n_windows']} "
            f"| {row['mean_count_mean']:.1f} "
            f"| {row['dispersion_index_mean']:.2f} ± {row['dispersion_index_sd']:.2f} "
            f"| {row['dispersion_across_run_cv']:.1%} "
            f"| {'yes' if row['enough_windows_for_reliable_dispersion'] else 'no'} |"
        )

    lines.extend([
        "",
        "## Method",
        "",
        "- Five independent runtime histories were simulated to the full 2,000,000-mile target.",
        "- Transition vectors, element counts, rarity assignments, and full-scenario calibration were held fixed. Duration, initial-state, and transition-sampling seeds varied by history.",
        "- The 100k, 200k, 500k, and 1M-mile results are exact prefixes of each corresponding 2M-mile history, which isolates the effect of observing less mileage.",
        "- Window statistics use complete, non-overlapping windows and sample variance. Dispersion is variance divided by mean episode count.",
        "- One-window cases are reported without dispersion because variance cannot be estimated from one observation.",
        "- Prefix unknown-time fractions merge all overlapping episode intervals and clip intervals at the prefix boundary.",
        f"- Total simulation wall time: {elapsed_seconds / 60:.1f} minutes.",
        "",
        "## Files",
        "",
        "- `mileage_runs.csv` and `mileage_summary.csv`: per-history and aggregate mileage results.",
        "- `window_runs.csv` and `window_summary.csv`: the complete mileage/window grid.",
        "- `summary.json`: manifest, per-run metadata, and aggregate results.",
        "- `runs/.../stats.json`: compact output for each independent full history.",
        "- `window_mileage_effects.png`: convergence and window-scale comparison.",
        "",
    ])
    (RESULTS_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    run_records = []
    mileage_rows = []
    window_rows = []
    for replicate in range(REPLICATES):
        run_record, run_mileage, run_windows = run_one(replicate)
        run_records.append(run_record)
        mileage_rows.extend(run_mileage)
        window_rows.extend(run_windows)
    elapsed_seconds = time.monotonic() - started

    mileage_summary = aggregate_mileage(mileage_rows)
    window_summary = aggregate_windows(window_rows)
    write_csv(RESULTS_DIR / "mileage_runs.csv", mileage_rows)
    write_csv(RESULTS_DIR / "mileage_summary.csv", mileage_summary)
    write_csv(RESULTS_DIR / "window_runs.csv", window_rows)
    write_csv(RESULTS_DIR / "window_summary.csv", window_summary)
    manifest = {
        "study": "window size and total simulated mileage sensitivity",
        "source_config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "mileage_levels": MILEAGE_LEVELS,
        "window_sizes": WINDOW_SIZES,
        "default_window_miles": DEFAULT_WINDOW,
        "replicates": REPLICATES,
        "runtime_seed_keys_varied": RUNTIME_SEED_KEYS,
        "minimum_windows_for_reliable_dispersion": MIN_WINDOWS_FOR_RELIABLE_DISPERSION,
        "total_wall_seconds": elapsed_seconds,
        "runs": run_records,
        "mileage_summary": mileage_summary,
        "window_summary": window_summary,
    }
    with (RESULTS_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    make_plots(mileage_summary, window_summary)
    write_report(mileage_summary, window_summary, elapsed_seconds)
    print(
        f"completed {REPLICATES} full histories and "
        f"{len(window_rows)} window analyses in {elapsed_seconds / 60:.1f} "
        f"minutes; results: {RESULTS_DIR}", flush=True,
    )


if __name__ == "__main__":
    main()
