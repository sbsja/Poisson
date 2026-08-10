"""Aggregate completed v6 parameter studies into a sensitivity ranking."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


STUDIES_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = Path(__file__).resolve().parent / "results"
PRIMARY_METRICS = ("episodes_per_hour", "unknown_time_fraction")
EXCLUDED = {
    "parameter_sensitivity_study",
    "seed_variability_study",
}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def seed_noise():
    path = STUDIES_DIR / "seed_variability_study" / "results" / "summary.json"
    data = load_json(path)
    rows = data["runs"]
    output = {}
    for metric in PRIMARY_METRICS:
        values = [float(row[metric]) for row in rows]
        output[metric] = {
            "mean": statistics.fmean(values),
            "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
            "minimum": min(values),
            "maximum": max(values),
            "runs": len(values),
        }
    return output


def collect_studies(noise):
    rows = []
    for summary_path in sorted(STUDIES_DIR.glob("*_study/results/summary.json")):
        data = load_json(summary_path)
        name = data.get("study", summary_path.parents[1].name)
        if name in EXCLUDED or len(data.get("summary", [])) < 2:
            continue
        row = {"study": name, "levels": len(data["summary"])}
        max_snr = 0.0
        for metric in PRIMARY_METRICS:
            means = [
                item.get(f"{metric}_mean") for item in data["summary"]
                if item.get(f"{metric}_mean") is not None
            ]
            if len(means) < 2:
                effect_range = 0.0
            else:
                effect_range = max(means) - min(means)
            baseline_mean = noise[metric]["mean"]
            baseline_sd = noise[metric]["sd"]
            snr = effect_range / baseline_sd if baseline_sd else math.inf
            percent = effect_range / baseline_mean * 100.0 if baseline_mean else math.inf
            row[f"{metric}_range"] = effect_range
            row[f"{metric}_range_percent"] = percent
            row[f"{metric}_snr"] = snr
            max_snr = max(max_snr, snr)
        row["maximum_primary_snr"] = max_snr
        rows.append(row)
    rows.sort(key=lambda item: item["maximum_primary_snr"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_plot(rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shown = list(reversed(rows[:20]))
    labels = [row["study"].replace("_study", "").replace("_", " ") for row in shown]
    rate = [row["episodes_per_hour_snr"] for row in shown]
    occupancy = [row["unknown_time_fraction_snr"] for row in shown]
    y = list(range(len(shown)))
    fig, axis = plt.subplots(figsize=(12, max(6, len(shown) * 0.42)))
    axis.barh([value - 0.2 for value in y], rate, height=0.38,
              label="episodes/hour", color="tab:blue")
    axis.barh([value + 0.2 for value in y], occupancy, height=0.38,
              label="unknown-time fraction", color="tab:orange")
    axis.set_yticks(y)
    axis.set_yticklabels(labels)
    axis.set_xlabel("effect range / seed-only standard deviation")
    axis.set_title("Current-v6 one-factor sensitivity ranking")
    axis.axvline(1.0, color="black", linestyle="--", alpha=0.6)
    axis.grid(axis="x", alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "sensitivity_tornado.png", dpi=160)
    plt.close(fig)

    # Cross-metric heatmap keeps rate and occupancy influence visible together.
    ordered = rows[:20]
    matrix = [
        [row["episodes_per_hour_snr"], row["unknown_time_fraction_snr"],
         row["episodes_per_hour_range_percent"],
         row["unknown_time_fraction_range_percent"]]
        for row in ordered
    ]
    transformed = [[math.log10(1.0 + max(value, 0.0)) for value in line]
                   for line in matrix]
    fig, axis = plt.subplots(figsize=(10, max(6, len(ordered) * 0.4)))
    image = axis.imshow(transformed, aspect="auto", cmap="viridis")
    axis.set_xticks(range(4))
    axis.set_xticklabels(["rate SNR", "occupancy SNR",
                          "rate range %", "occupancy range %"], rotation=25,
                         ha="right")
    axis.set_yticks(range(len(ordered)))
    axis.set_yticklabels([
        row["study"].replace("_study", "").replace("_", " ")
        for row in ordered
    ], fontsize=8)
    axis.set_title("Sensitivity across primary metrics (log-scaled color)")
    fig.colorbar(image, ax=axis, label="log10(1 + value)")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "sensitivity_metric_heatmap.png", dpi=160)
    plt.close(fig)

    # A study above and to the right of the seed-noise reference affects both
    # episode frequency and time occupancy over its tested range.
    fig, (axis, key_axis) = plt.subplots(
        1, 2, figsize=(13, 7), gridspec_kw={"width_ratios": [3.2, 1.8]})
    for row in rows:
        x = row["episodes_per_hour_snr"]
        y_value = row["unknown_time_fraction_snr"]
        axis.scatter(x, y_value, s=90, color="tab:blue")
        axis.annotate(str(row["rank"]), (x, y_value), ha="center", va="center",
                      fontsize=7, color="white", fontweight="bold")
    axis.axvline(1.0, color="0.3", linestyle="--")
    axis.axhline(1.0, color="0.3", linestyle="--")
    axis.set_xscale("symlog", linthresh=1.0)
    axis.set_yscale("symlog", linthresh=1.0)
    axis.set_xlabel("episode-rate signal / seed noise")
    axis.set_ylabel("occupancy signal / seed noise")
    axis.set_title("Effect-versus-noise map")
    axis.grid(alpha=0.25, which="both")
    key_axis.axis("off")
    key_axis.set_title("Study key", loc="left")
    for position, row in enumerate(rows):
        key_axis.text(
            0.0, 1.0 - (position + 0.5) / len(rows),
            f"{row['rank']:>2}  "
            + row["study"].replace("_study", "").replace("_", " "),
            transform=key_axis.transAxes, va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "effect_noise_scatter.png", dpi=160)
    plt.close(fig)


def write_report(rows, noise):
    lines = [
        "# Parameter-sensitivity study (v6)",
        "",
        "This report aggregates the specifically named current-v6 studies. "
        "It replaces the legacy ranking based on removed unknown mechanisms.",
        "",
        "## Seed-only noise control",
        "",
        "| metric | mean | seed SD | runs |",
        "|---|---:|---:|---:|",
    ]
    for metric in PRIMARY_METRICS:
        row = noise[metric]
        lines.append(
            f"| {metric} | {row['mean']:.6g} | {row['sd']:.6g} | {row['runs']} |"
        )
    lines.extend([
        "",
        "## Ranking",
        "",
        "SNR is the range across a study's swept level means divided by the "
        "seed-only standard deviation. Structural and categorical studies are "
        "ranked by range but should not be interpreted as linear trends.",
        "",
        "| rank | study | levels | rate SNR | rate range % | occupancy SNR | occupancy range % |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['study']} | {row['levels']} "
            f"| {row['episodes_per_hour_snr']:.2f} "
            f"| {row['episodes_per_hour_range_percent']:.1f}% "
            f"| {row['unknown_time_fraction_snr']:.2f} "
            f"| {row['unknown_time_fraction_range_percent']:.1f}% |"
        )
    lines.extend([
        "",
        "## Limitations",
        "",
        "The component studies are screening runs. Wide grids intentionally "
        "include extreme settings, so the ranking describes the tested ranges, "
        "not an intrinsic unit-free importance. Confirm the leading factors with "
        "longer paired runs and interaction studies.",
        "",
        "## Charts",
        "",
        "- `sensitivity_tornado.png`: ranked rate and occupancy SNR.",
        "- `sensitivity_metric_heatmap.png`: cross-metric comparison.",
        "- `effect_noise_scatter.png`: factors affecting rate, occupancy, or both.",
        "",
    ])
    (RESULTS_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    noise = seed_noise()
    rows = collect_studies(noise)
    if not rows:
        raise RuntimeError("No completed v6 component studies were found")
    write_csv(RESULTS_DIR / "sensitivity_ranking.csv", rows)
    payload = {"study": "parameter_sensitivity_study", "seed_noise": noise,
               "ranking": rows}
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    make_plot(rows)
    write_report(rows, noise)
    print(f"[parameter_sensitivity_study] ranked {len(rows)} completed studies")
    return payload


if __name__ == "__main__":
    main()
