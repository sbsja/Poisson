"""Study-specific static charts generated from v6 summary manifests."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np


PRIMARY = (
    ("episodes_per_hour", "Episodes per hour"),
    ("unknown_time_fraction", "Unknown-time fraction"),
    ("episode_duration_p90_seconds", "Duration p90 (seconds)"),
    ("dispersion_index", "Dispersion index"),
)


def _plt():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _finite(value):
    return value is not None and math.isfinite(float(value))


def _means(data, metric):
    return [row.get(f"{metric}_mean") for row in data["summary"]]


def _finish(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    _plt().close(fig)


def replicate_response(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    labels = [row["label"] for row in data["levels"]]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(2, 2, figsize=(max(12, len(labels) * 0.32), 8))
    for axis, (metric, title) in zip(axes.flat, PRIMARY):
        for replicate in sorted({row["replicate"] for row in data["runs"]}):
            group = [row for row in data["runs"] if row["replicate"] == replicate]
            by_level = {row["level_index"]: row.get(metric) for row in group}
            valid = [(index, by_level.get(index)) for index in range(len(labels))
                     if _finite(by_level.get(index))]
            if valid:
                axis.plot([item[0] for item in valid], [item[1] for item in valid],
                          marker="o", ms=3, lw=0.8, alpha=0.35,
                          label=f"seed {replicate}")
        means = _means(data, metric)
        valid = [(index, value) for index, value in enumerate(means) if _finite(value)]
        if valid:
            axis.plot([item[0] for item in valid], [item[1] for item in valid],
                      color="black", marker="o", ms=4, lw=1.8, label="mean")
        axis.set_title(title)
        axis.set_xticks(x)
        axis.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
        axis.grid(alpha=0.25)
    axes[0, 0].legend(fontsize=7, ncol=2)
    fig.suptitle(data["study"].replace("_", " ").title() + ": paired replicates")
    filename = "paired_replicate_responses.png"
    _finish(fig, results_dir / filename)
    return filename


def c_size_composition(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    labels = [row["label"] for row in data["levels"]]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(max(11, len(labels) * 0.3), 5.5))
    bottom = np.zeros(len(labels))
    colors = {3: "tab:blue", 4: "tab:orange", 5: "tab:green", 6: "tab:red"}
    for size in (3, 4, 5, 6):
        values = np.asarray([
            0.0 if row.get(f"c{size}_episodes_mean") is None
            else row[f"c{size}_episodes_mean"]
            for row in data["summary"]])
        ax.bar(x, values, bottom=bottom, label=f"C{size}", color=colors[size])
        bottom += values
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("mean episodes per run")
    ax.set_title("Episode composition by exact-combination size")
    ax.legend(ncol=4)
    ax.grid(alpha=0.25, axis="y")
    filename = "c_size_composition.png"
    _finish(fig, results_dir / filename)
    return filename


def mechanism_relationships(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    pairs = (
        ("selected_rule_mass_sum", "episodes_per_hour",
         "Selected rule mass", "episodes/hour"),
        ("total_layer_transitions", "episodes_per_hour",
         "layer transitions", "episodes/hour"),
        ("total_events", "wall_seconds", "events", "wall seconds"),
    )
    color_values = np.asarray([row["level_index"] for row in data["runs"]])
    for axis, (x_metric, y_metric, xlabel, ylabel) in zip(axes, pairs):
        points = [(row.get(x_metric), row.get(y_metric), color_values[index])
                  for index, row in enumerate(data["runs"])
                  if _finite(row.get(x_metric)) and _finite(row.get(y_metric))]
        if points:
            axis.scatter([item[0] for item in points], [item[1] for item in points],
                         c=[item[2] for item in points], cmap="viridis",
                         s=24, alpha=0.7)
        axis.set_xlabel(xlabel)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
    axes[0].set_title("Rule coverage and response")
    axes[1].set_title("Turnover and response")
    axes[2].set_title("Computational scaling")
    filename = "mechanism_relationships.png"
    _finish(fig, results_dir / filename)
    return filename


def normalized_metric_heatmap(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    metrics = PRIMARY + (
        ("total_layer_transitions", "Layer transitions"),
        ("selected_rule_mass_sum", "Selected rule mass"),
        ("wall_seconds", "Wall time"),
    )
    matrix = []
    for metric, _label in metrics:
        values = np.asarray([
            np.nan if not _finite(value) else float(value)
            for value in _means(data, metric)], dtype=float)
        finite = values[np.isfinite(values)]
        if len(finite) and max(finite) > min(finite):
            values = (values - min(finite)) / (max(finite) - min(finite))
        elif len(finite):
            values[np.isfinite(values)] = 0.5
        matrix.append(values)
    matrix = np.asarray(matrix)
    labels = [row["label"] for row in data["levels"]]
    fig, ax = plt.subplots(figsize=(max(11, len(labels) * 0.3), 5.5))
    image = ax.imshow(matrix, aspect="auto", vmin=0.0, vmax=1.0, cmap="viridis")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels([label for _metric, label in metrics], fontsize=8)
    ax.set_title("Within-study normalized response heatmap")
    fig.colorbar(image, ax=ax, label="0 = lowest tested mean, 1 = highest")
    filename = "normalized_response_heatmap.png"
    _finish(fig, results_dir / filename)
    return filename


def grouped_heatmap(results_dir: Path, data: dict[str, Any], group_key: str) -> str:
    plt = _plt()
    groups = []
    for level in data["levels"]:
        group = level.get(group_key)
        if group is not None and group not in groups:
            groups.append(group)
    values = sorted({float(level["value"]) for level in data["levels"]
                     if level.get(group_key) is not None and _finite(level.get("value"))})
    fig, axes = plt.subplots(1, 2, figsize=(max(11, len(values) * 0.8),
                                           max(5, len(groups) * 0.55 + 2)))
    for axis, (metric, title) in zip(axes, PRIMARY[:2]):
        matrix = np.full((len(groups), len(values)), np.nan)
        for index, level in enumerate(data["levels"]):
            if level.get(group_key) not in groups or not _finite(level.get("value")):
                continue
            row = groups.index(level[group_key])
            column = values.index(float(level["value"]))
            matrix[row, column] = data["summary"][index].get(f"{metric}_mean")
        image = axis.imshow(matrix, aspect="auto", cmap="viridis")
        axis.set_xticks(range(len(values)))
        axis.set_xticklabels([f"{value:g}" for value in values], rotation=45,
                             ha="right", fontsize=8)
        axis.set_yticks(range(len(groups)))
        axis.set_yticklabels([str(group).replace("_", " ") for group in groups],
                             fontsize=8)
        axis.set_xlabel("tested value / multiplier")
        axis.set_title(title)
        fig.colorbar(image, ax=axis, shrink=0.8)
    filename = f"{group_key}_response_heatmap.png"
    _finish(fig, results_dir / filename)
    return filename


def numeric_response(results_dir: Path, data: dict[str, Any], log_x=False) -> str:
    plt = _plt()
    pairs = [(index, float(level["value"]))
             for index, level in enumerate(data["levels"])
             if _finite(level.get("value"))]
    pairs.sort(key=lambda item: item[1])
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for axis, (metric, title) in zip(axes.flat, PRIMARY):
        xs, means, sds = [], [], []
        for index, value in pairs:
            mean = data["summary"][index].get(f"{metric}_mean")
            if not _finite(mean):
                continue
            xs.append(value)
            means.append(mean)
            sd = data["summary"][index].get(f"{metric}_sd")
            sds.append(0.0 if not _finite(sd) else sd)
        if xs:
            axis.errorbar(xs, means, yerr=sds, marker="o", capsize=3)
        if log_x and xs and min(xs) > 0:
            axis.set_xscale("log")
        axis.set_xlabel("tested value")
        axis.set_title(title)
        axis.grid(alpha=0.25)
    filename = "numeric_response_curves.png"
    _finish(fig, results_dir / filename)
    return filename


def selection_sweeps(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    sweeps = []
    for level in data["levels"]:
        if level.get("sweep") not in sweeps:
            sweeps.append(level.get("sweep"))
    fig, axes = plt.subplots(len(sweeps), 2, figsize=(11, 4 * len(sweeps)),
                             squeeze=False)
    for row_index, sweep in enumerate(sweeps):
        indices = [index for index, level in enumerate(data["levels"])
                   if level.get("sweep") == sweep]
        indices.sort(key=lambda index: float(data["levels"][index]["value"]))
        for axis, (metric, title) in zip(axes[row_index], PRIMARY[:2]):
            xs = [data["levels"][index]["value"] for index in indices]
            ys = [data["summary"][index][f"{metric}_mean"] for index in indices]
            sds = [data["summary"][index][f"{metric}_sd"] for index in indices]
            axis.errorbar(xs, ys, yerr=sds, marker="o", capsize=3)
            axis.set_xlabel(f"{sweep} selection percentage")
            axis.set_title(title)
            axis.grid(alpha=0.25)
    filename = "selection_percentage_sweeps.png"
    _finish(fig, results_dir / filename)
    return filename


def configured_vs_observed_sizes(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    labels = [level["label"] for level in data["levels"]]
    x = np.arange(len(labels))
    colors = {3: "tab:blue", 4: "tab:orange", 5: "tab:green", 6: "tab:red"}
    fig, axes = plt.subplots(2, 1, figsize=(max(11, len(labels) * 0.5), 8), sharex=True)
    for axis, source, title in (
        (axes[0], "configured", "Configured selected rules"),
        (axes[1], "observed", "Observed episodes"),
    ):
        bottom = np.zeros(len(labels))
        for size in (3, 4, 5, 6):
            if source == "configured":
                values = [float(level.get("counts", {}).get(str(size),
                          level.get("counts", {}).get(size, 0))) for level in data["levels"]]
            else:
                values = [float(row.get(f"c{size}_episodes_mean") or 0.0)
                          for row in data["summary"]]
            axis.bar(x, values, bottom=bottom, color=colors[size], label=f"C{size}")
            bottom += np.asarray(values)
        axis.set_ylabel("count")
        axis.set_title(title)
        axis.legend(ncol=4)
        axis.grid(alpha=0.25, axis="y")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    filename = "configured_vs_observed_combination_sizes.png"
    _finish(fig, results_dir / filename)
    return filename


def seed_caterpillar(results_dir: Path, data: dict[str, Any]) -> str:
    plt = _plt()
    rows = sorted(data["runs"], key=lambda row: row["episodes_per_hour"])
    y = np.arange(len(rows))
    fig, axes = plt.subplots(1, 2, figsize=(12, max(5, len(rows) * 0.28)))
    for axis, metric, title in (
        (axes[0], "episodes_per_hour", "Episode-rate seed variability"),
        (axes[1], "unknown_time_fraction", "Occupancy seed variability"),
    ):
        values = [row[metric] for row in rows]
        axis.scatter(values, y, s=30)
        axis.axvline(np.mean(values), color="tab:red", ls="--", label="mean")
        axis.set_yticks(y)
        axis.set_yticklabels([row["level_label"] for row in rows], fontsize=7)
        axis.set_xlabel(metric.replace("_", " "))
        axis.set_title(title)
        axis.grid(alpha=0.25, axis="x")
        axis.legend(fontsize=8)
    filename = "seed_caterpillar.png"
    _finish(fig, results_dir / filename)
    return filename


def update_report(results_dir: Path, filenames: list[str]) -> None:
    path = results_dir / "report.md"
    if not path.exists():
        return
    marker = "## Additional study-specific charts"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n"
    lines = ["", marker, ""]
    lines.extend(f"- `{filename}`" for filename in filenames)
    lines.append("")
    path.write_text(text + "\n".join(lines), encoding="utf-8")


def generate_study_charts(results_dir: Path, data: dict[str, Any]) -> list[str]:
    """Generate universal and study-routed plots from one summary manifest."""
    results_dir = Path(results_dir)
    filenames = [
        replicate_response(results_dir, data),
        c_size_composition(results_dir, data),
        mechanism_relationships(results_dir, data),
        normalized_metric_heatmap(results_dir, data),
    ]
    levels = data["levels"]
    name = data["study"]
    if any("sweep" in study_level for study_level in levels):
        filenames.append(selection_sweeps(results_dir, data))
    if any("layer" in study_level for study_level in levels):
        filenames.append(grouped_heatmap(results_dir, data, "layer"))
    elif any("rarity" in study_level for study_level in levels):
        filenames.append(grouped_heatmap(results_dir, data, "rarity"))
    if any("counts" in study_level for study_level in levels):
        filenames.append(configured_vs_observed_sizes(results_dir, data))
    numeric_count = sum(_finite(study_level.get("value")) for study_level in levels)
    has_grouped_axis = any(
        any(key in study_level for key in ("sweep", "layer", "rarity"))
        for study_level in levels
    )
    if (numeric_count >= max(2, len(levels) - 1)
            and not has_grouped_axis
            and name not in {"duration_distribution_study",
                             "combination_size_study",
                             "seed_variability_study"}):
        log_x = name in {
            "concentration_scale_study", "target_total_hours_study",
            "average_speed_study", "mileage_window_study",
            "minimum_duration_study",
        }
        filenames.append(numeric_response(results_dir, data, log_x=log_x))
    if name == "seed_variability_study":
        filenames.append(seed_caterpillar(results_dir, data))
    update_report(results_dir, filenames)
    return filenames
