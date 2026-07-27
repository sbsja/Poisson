"""Study alternative duration distributions for one simulator element.

The target is the default model's sole unknown ego-maneuver element.  Every
candidate has the configured ego mean (30 s) and variance (400 s^2), and is
used only when that element is selected.  Every other element retains the
production Gamma duration model.
"""

from __future__ import annotations

import csv
import gc
import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats


STUDY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDY_DIR.parents[1]
RESULTS_DIR = STUDY_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

TARGET_LAYER_KEY = "ego_maneuver"
TARGET_LAYER_INDEX = 2
DISTRIBUTIONS = ("gamma", "weibull", "lognormal", "inverse_gaussian")
REPLICATES = 3
DURATION_SEED_STEP = 1_000_003
TARGET_SEED_OFFSET = 80_081
QUANTILE_BUFFER_SIZE = 65_536

sys.path.insert(0, str(PROJECT_ROOT))

from simulator import ScenarioSimulator, SimConfig  # noqa: E402


DISPLAY_NAMES = {
    "gamma": "Gamma (current)",
    "weibull": "Weibull",
    "lognormal": "Lognormal",
    "inverse_gaussian": "Inverse Gaussian",
}

RATIONALES = {
    "gamma": "current positive waiting-time model; moderate right tail",
    "weibull": "time-to-completion model with an elapsed-time-dependent hazard",
    "lognormal": "multiplicative delays; allows occasional long maneuvers",
    "inverse_gaussian": "first-passage/completion-time model with a strong right tail",
}


def mean(values):
    return statistics.fmean(values)


def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def percentile(values, quantile):
    return float(np.percentile(np.asarray(values, dtype=float), quantile))


def solve_weibull_shape(mean_seconds, variance_seconds2):
    """Find Weibull shape from its coefficient of variation."""
    target_cv2 = variance_seconds2 / mean_seconds ** 2
    low, high = 0.1, 20.0
    for _ in range(100):
        shape = (low + high) / 2.0
        g1 = math.gamma(1.0 + 1.0 / shape)
        cv2 = math.gamma(1.0 + 2.0 / shape) / (g1 * g1) - 1.0
        if cv2 > target_cv2:
            low = shape
        else:
            high = shape
    return (low + high) / 2.0


def distribution_spec(name, mean_seconds, variance_seconds2):
    """Return a frozen SciPy distribution with the requested moments."""
    if name == "gamma":
        shape = mean_seconds ** 2 / variance_seconds2
        scale = variance_seconds2 / mean_seconds
        return stats.gamma(a=shape, scale=scale), {
            "shape": shape, "scale": scale,
        }
    if name == "lognormal":
        sigma2 = math.log1p(variance_seconds2 / mean_seconds ** 2)
        sigma = math.sqrt(sigma2)
        mu = math.log(mean_seconds) - sigma2 / 2.0
        return stats.lognorm(s=sigma, scale=math.exp(mu)), {
            "log_mean": mu, "log_sd": sigma,
        }
    if name == "weibull":
        shape = solve_weibull_shape(mean_seconds, variance_seconds2)
        scale = mean_seconds / math.gamma(1.0 + 1.0 / shape)
        return stats.weibull_min(c=shape, scale=scale), {
            "shape": shape, "scale": scale,
        }
    if name == "inverse_gaussian":
        classical_shape = mean_seconds ** 3 / variance_seconds2
        scipy_mu = mean_seconds / classical_shape
        return stats.invgauss(mu=scipy_mu, scale=classical_shape), {
            "mean": mean_seconds, "shape": classical_shape,
        }
    raise ValueError(f"Unsupported distribution: {name}")


class QuantileSampler:
    """Vectorized inverse-CDF sampler using one common uniform per duration."""

    def __init__(self, frozen_distribution, seed, min_duration):
        self.distribution = frozen_distribution
        self.rng = np.random.default_rng(seed)
        self.min_duration = min_duration
        self.buffer = np.empty(0, dtype=float)
        self.position = 0
        self.samples = []

    def sample(self):
        if self.position >= len(self.buffer):
            uniforms = self.rng.random(QUANTILE_BUFFER_SIZE)
            self.buffer = np.maximum(
                self.distribution.ppf(uniforms), self.min_duration
            )
            self.position = 0
        value = float(self.buffer[self.position])
        self.position += 1
        self.samples.append(value)
        return value


class TargetDurationRng:
    """Intercept Gamma calls only for the selected current element."""

    def __init__(self, base_rng, current, target_index, target_shape,
                 target_scale, target_sampler):
        self.base_rng = base_rng
        self.current = current
        self.target_index = target_index
        self.target_shape = target_shape
        self.target_scale = target_scale
        self.target_sampler = target_sampler

    def gammavariate(self, shape, scale):
        is_target_layer = (
            math.isclose(shape, self.target_shape, rel_tol=0.0, abs_tol=1e-12)
            and math.isclose(scale, self.target_scale,
                             rel_tol=0.0, abs_tol=1e-12)
        )
        if is_target_layer and self.current[TARGET_LAYER_INDEX] == self.target_index:
            return self.target_sampler.sample()
        return self.base_rng.gammavariate(shape, scale)


def configure_run(distribution_name, replicate):
    cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    cfg.seeds = dict(cfg.seeds)
    cfg.seeds["duration"] += replicate * DURATION_SEED_STEP
    sim = ScenarioSimulator(cfg)
    layer = sim.layers[TARGET_LAYER_INDEX]
    unknown_indices = [i for i, flag in enumerate(layer.is_unknown) if flag]
    if len(unknown_indices) != 1:
        raise RuntimeError(
            f"Expected one unknown ego element, found {len(unknown_indices)}"
        )
    target_index = unknown_indices[0]
    target_name = layer.names[target_index]

    # The initial state is constructed with production behavior.  In the
    # current fixed initial-state seed it is a known element, so every visit to
    # the target receives the study distribution below.
    state = sim._new_state()
    if state["current"][TARGET_LAYER_INDEX] == target_index:
        raise RuntimeError(
            "The target is initially active; the study requires a known "
            "initial ego element so every target duration is intercepted."
        )

    params = cfg.layers[TARGET_LAYER_KEY]
    frozen, fitted_parameters = distribution_spec(
        distribution_name, params.mean_duration, params.variance_duration
    )
    target_seed = (
        cfg.seeds["duration"] + TARGET_SEED_OFFSET
    )
    sampler = QuantileSampler(
        frozen, target_seed, cfg.min_duration_seconds
    )
    sim.rng_duration = TargetDurationRng(
        sim.rng_duration,
        state["current"],
        target_index,
        layer.gamma_shape,
        layer.gamma_scale,
        sampler,
    )
    return cfg, sim, state, target_index, target_name, sampler, fitted_parameters


def run_one(distribution_name, replicate):
    (cfg, sim, state, target_index, target_name, sampler,
     fitted_parameters) = configure_run(distribution_name, replicate)
    started = time.monotonic()
    result, final_state = sim.run_resumable(state=state)
    wall_seconds = time.monotonic() - started
    if result is None:
        raise RuntimeError("Unexpected incomplete simulation")

    target_episodes = [
        episode for episode in result.episodes
        if episode.layer == TARGET_LAYER_KEY and episode.element == target_name
    ]
    episode_durations = [episode.duration_seconds for episode in target_episodes]
    sojourns = sampler.samples
    ego_stats = result.layer_stats[TARGET_LAYER_INDEX]
    type_counts = result.episodes_by_type()
    row = {
        "distribution": distribution_name,
        "distribution_display_name": DISPLAY_NAMES[distribution_name],
        "replicate": replicate + 1,
        "duration_seed": cfg.seeds["duration"],
        "target_duration_seed": cfg.seeds["duration"] + TARGET_SEED_OFFSET,
        "target_layer": TARGET_LAYER_KEY,
        "target_element": target_name,
        "configured_mean_seconds": cfg.layers[TARGET_LAYER_KEY].mean_duration,
        "configured_variance_seconds2": cfg.layers[
            TARGET_LAYER_KEY
        ].variance_duration,
        "fitted_parameters": fitted_parameters,
        "target_sojourn_samples": len(sojourns),
        "target_sojourn_mean_seconds": mean(sojourns),
        "target_sojourn_variance_seconds2": statistics.variance(sojourns),
        "target_sojourn_p90_seconds": percentile(sojourns, 90),
        "target_sojourn_p99_seconds": percentile(sojourns, 99),
        "target_sojourn_max_seconds": max(sojourns),
        "target_episode_count": len(target_episodes),
        "target_episode_mean_seconds": mean(episode_durations),
        "target_episode_median_seconds": percentile(episode_durations, 50),
        "target_episode_p90_seconds": percentile(episode_durations, 90),
        "target_episode_p99_seconds": percentile(episode_durations, 99),
        "target_episode_max_seconds": max(episode_durations),
        "target_occupancy_fraction": ego_stats["empirical_unknown_occupancy"],
        "total_unknown_episodes": len(result.episodes),
        "full_scenario_episodes": type_counts["full_scenario"],
        "total_unknown_time_fraction": result.unknown_time_fraction(),
        "total_events": result.total_events,
        "simulated_miles": result.total_miles,
        "wall_seconds": wall_seconds,
    }

    run_dir = RESULTS_DIR / "runs" / distribution_name / f"replicate_{replicate + 1}"
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "stats.json").open("w", encoding="utf-8") as handle:
        json.dump(row, handle, indent=2)
    print(
        f"{DISPLAY_NAMES[distribution_name]:>18s} "
        f"replicate={replicate + 1}/{REPLICATES} "
        f"target_episodes={len(target_episodes):>6,} "
        f"mean={row['target_episode_mean_seconds']:>6.2f}s "
        f"p99={row['target_episode_p99_seconds']:>7.2f}s "
        f"wall={wall_seconds:.1f}s",
        flush=True,
    )
    del result, final_state, sim, state, target_episodes, episode_durations
    gc.collect()
    return row


def aggregate(rows):
    metrics = (
        "target_sojourn_mean_seconds",
        "target_sojourn_variance_seconds2",
        "target_sojourn_p99_seconds",
        "target_episode_count",
        "target_episode_mean_seconds",
        "target_episode_median_seconds",
        "target_episode_p90_seconds",
        "target_episode_p99_seconds",
        "target_episode_max_seconds",
        "target_occupancy_fraction",
        "total_unknown_episodes",
        "full_scenario_episodes",
        "total_unknown_time_fraction",
        "total_events",
        "wall_seconds",
    )
    out = []
    for distribution_name in DISTRIBUTIONS:
        group = [row for row in rows if row["distribution"] == distribution_name]
        summary = {
            "distribution": distribution_name,
            "distribution_display_name": DISPLAY_NAMES[distribution_name],
            "runs": len(group),
        }
        for metric in metrics:
            values = [row[metric] for row in group]
            summary[f"{metric}_mean"] = mean(values)
            summary[f"{metric}_sd"] = sample_sd(values)
            summary[f"{metric}_min"] = min(values)
            summary[f"{metric}_max"] = max(values)
        out.append(summary)
    return out


def write_csv(path, rows):
    flat_rows = []
    for row in rows:
        flat_rows.append({
            key: value for key, value in row.items()
            if not isinstance(value, dict)
        })
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)


def make_plot(rows, summary_rows, mean_seconds, variance_seconds2):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {
        "gamma": "tab:blue",
        "weibull": "tab:green",
        "lognormal": "tab:orange",
        "inverse_gaussian": "tab:red",
    }
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    x = np.linspace(1.0, 180.0, 700)
    for name in DISTRIBUTIONS:
        frozen, _params = distribution_spec(name, mean_seconds, variance_seconds2)
        axes[0, 0].plot(
            x, frozen.pdf(x), label=DISPLAY_NAMES[name], color=colors[name]
        )
    axes[0, 0].set_title("Candidate sojourn-time shapes")
    axes[0, 0].set_xlabel("duration (seconds)")
    axes[0, 0].set_ylabel("probability density")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(alpha=0.25)

    labels = [row["distribution_display_name"] for row in summary_rows]
    positions = np.arange(len(labels))

    def bar_panel(axis, metric, title, ylabel):
        values = [row[f"{metric}_mean"] for row in summary_rows]
        errors = [row[f"{metric}_sd"] for row in summary_rows]
        axis.bar(
            positions, values, yerr=errors, capsize=4,
            color=[colors[row["distribution"]] for row in summary_rows],
            alpha=0.82,
        )
        for distribution_index, name in enumerate(DISTRIBUTIONS):
            for row in rows:
                if row["distribution"] == name:
                    axis.scatter(
                        distribution_index, row[metric], color="black",
                        alpha=0.45, s=15, zorder=3,
                    )
        axis.set_xticks(positions)
        axis.set_xticklabels(labels, rotation=15, ha="right")
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25, axis="y")

    bar_panel(
        axes[0, 1], "target_episode_mean_seconds",
        "Mean ego_008 episode duration", "seconds",
    )
    bar_panel(
        axes[1, 0], "target_episode_p99_seconds",
        "99th-percentile ego_008 episode duration", "seconds",
    )
    bar_panel(
        axes[1, 1], "total_unknown_time_fraction",
        "Union unknown-time fraction", "fraction of simulated time",
    )
    fig.suptitle(
        "Duration-distribution sensitivity for ego_008\n"
        "mean 30 s, variance 400 s²; mean ± sample SD across 3 full runs",
        fontsize=14,
    )
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "duration_distribution_effects.png", dpi=160)
    plt.close(fig)


def write_report(rows, summary_rows, elapsed_seconds):
    gamma = next(row for row in summary_rows if row["distribution"] == "gamma")
    largest_tail = max(
        summary_rows, key=lambda row: row["target_episode_p99_seconds_mean"]
    )
    episode_counts = [row["target_episode_count_mean"] for row in summary_rows]
    occupancy = [row["target_occupancy_fraction_mean"] for row in summary_rows]
    count_spread = (max(episode_counts) - min(episode_counts)) / mean(episode_counts)
    occupancy_spread = (max(occupancy) - min(occupancy)) / mean(occupancy)

    lines = [
        "# Duration-distribution study for `ego_008`",
        "",
        "## Outcome",
        "",
        (
            "Changing the duration distribution mainly changes the **tail of "
            "episode duration**, not how often the element is selected. All "
            "four candidates have the same theoretical 30-second mean and "
            "400 s² variance, so their average occupancy remains close; their "
            "rare long-duration behavior is different."
        ),
        "",
        (
            f"Across candidates, mean target-episode counts differed by only "
            f"{count_spread:.1%}, while mean target occupancy differed by "
            f"{occupancy_spread:.1%}. The largest average 99th-percentile "
            f"episode duration came from **{largest_tail['distribution_display_name']}** "
            f"at {largest_tail['target_episode_p99_seconds_mean']:.1f} seconds, "
            f"versus {gamma['target_episode_p99_seconds_mean']:.1f} seconds "
            "for the current Gamma model."
        ),
        "",
        "**Recommendation:** retain Gamma as the neutral production default "
        "unless measured maneuver-duration data supports another family. Use "
        "Lognormal or Inverse Gaussian as tail-stress alternatives when the "
        "safety question is sensitivity to unusually long maneuvers; use "
        "Weibull when completion likelihood is expected to change with elapsed time.",
        "",
        "## Aggregate simulation results",
        "",
        "Each cell is the mean across three full runs; `±` is sample standard deviation.",
        "",
        "| distribution | target episodes | episode mean | episode p90 | episode p99 | target occupancy | all unknown episodes | union unknown time |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['distribution_display_name']} "
            f"| {row['target_episode_count_mean']:,.0f} ± {row['target_episode_count_sd']:,.0f} "
            f"| {row['target_episode_mean_seconds_mean']:.2f} ± {row['target_episode_mean_seconds_sd']:.2f} s "
            f"| {row['target_episode_p90_seconds_mean']:.1f} ± {row['target_episode_p90_seconds_sd']:.1f} s "
            f"| {row['target_episode_p99_seconds_mean']:.1f} ± {row['target_episode_p99_seconds_sd']:.1f} s "
            f"| {row['target_occupancy_fraction_mean']:.3%} ± {row['target_occupancy_fraction_sd']:.3%} "
            f"| {row['total_unknown_episodes_mean']:,.0f} ± {row['total_unknown_episodes_sd']:,.0f} "
            f"| {row['total_unknown_time_fraction_mean']:.3%} ± {row['total_unknown_time_fraction_sd']:.3%} |"
        )
    lines.extend([
        "",
        "## Why these distributions",
        "",
    ])
    for name in DISTRIBUTIONS:
        lines.append(f"- **{DISPLAY_NAMES[name]}:** {RATIONALES[name]}.")
    lines.extend([
        "",
        "## Method",
        "",
        "- Target: `ego_008`, the sole unknown ego-maneuver element in the current seeded configuration.",
        "- 12 end-to-end simulations: four distributions × three duration seeds.",
        "- Every run used the full configured 2,000,000-mile target.",
        "- Only `ego_008` used the candidate distribution. Every other element retained the production Gamma model.",
        "- Candidate durations were generated from common uniform quantiles using a dedicated target-element seed. This prevents target draws from consuming the shared duration RNG used by other elements.",
        "- All candidates use theoretical mean 30 seconds and variance 400 s², followed by the simulator's existing one-second lower clamp.",
        "- The production simulator and root configuration were not modified; the adapter exists only in this study runner.",
        f"- Total study wall time: {elapsed_seconds / 60:.1f} minutes.",
        "",
        "## Files",
        "",
        "- `runs.csv`: one row per simulation.",
        "- `summary.csv`: distribution-level means, standard deviations, minima, and maxima.",
        "- `summary.json`: study manifest, fitted parameters, per-run results, and aggregate results.",
        "- `runs/.../stats.json`: compact output for each individual run.",
        "- `duration_distribution_effects.png`: distribution shapes and outcome comparison.",
        "",
    ])
    (RESULTS_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base_cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    params = base_cfg.layers[TARGET_LAYER_KEY]
    fitted = {
        name: distribution_spec(
            name, params.mean_duration, params.variance_duration
        )[1]
        for name in DISTRIBUTIONS
    }
    started = time.monotonic()
    rows = []
    for name in DISTRIBUTIONS:
        for replicate in range(REPLICATES):
            rows.append(run_one(name, replicate))
    elapsed_seconds = time.monotonic() - started
    summary_rows = aggregate(rows)

    write_csv(RESULTS_DIR / "runs.csv", rows)
    write_csv(RESULTS_DIR / "summary.csv", summary_rows)
    manifest = {
        "study": "duration distribution sensitivity for one element",
        "source_config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "target_layer": TARGET_LAYER_KEY,
        "target_element": rows[0]["target_element"],
        "distributions": DISTRIBUTIONS,
        "distribution_rationales": RATIONALES,
        "fitted_parameters": fitted,
        "configured_mean_seconds": params.mean_duration,
        "configured_variance_seconds2": params.variance_duration,
        "minimum_duration_seconds": base_cfg.min_duration_seconds,
        "replicates_per_distribution": REPLICATES,
        "total_wall_seconds": elapsed_seconds,
        "runs": rows,
        "summary": summary_rows,
    }
    with (RESULTS_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    make_plot(rows, summary_rows, params.mean_duration, params.variance_duration)
    write_report(rows, summary_rows, elapsed_seconds)
    print(
        f"completed {len(rows)} full simulations in {elapsed_seconds / 60:.1f} "
        f"minutes; results: {RESULTS_DIR}", flush=True,
    )


if __name__ == "__main__":
    main()
