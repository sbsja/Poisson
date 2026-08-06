#!/usr/bin/env python3
"""Run the layered scenario simulation (unknown-episode semantics).

Outputs (in --outdir):
  episodes.csv     one row per unknown episode (positions, duration, layer)
  windows.csv      episode-start count per fixed mileage window
  summary.md       results summary + verification
  stats.json       machine-readable statistics
  plots/*.png      cumulative episodes, duration histogram, inter-arrival
                   histogram, window counts, per-layer stats, street mix
  duration_distributions/
                   one Gamma PDF/CDF comparison per layer + manifest.json
"""

import argparse
import csv
import json
import math
import os
import pickle
import sys
import time

import numpy as np

from simulator import (LAYER_DEFINITIONS, RARITIES, ScenarioSimulator,
                       SimConfig)


def write_episodes_csv(path, result, inter_mi, inter_s):
    metadata = {}
    for layer_stats in result.layer_stats:
        for element in layer_stats["elements"]:
            metadata[(layer_stats["layer"], element["id"])] = (
                element["label"], element["description"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["episode_index", "type", "layer", "element",
                    "start_mileage", "end_mileage",
                    "start_time_seconds", "end_time_seconds",
                    "duration_seconds", "duration_miles", "truncated",
                    "inter_arrival_miles", "inter_arrival_seconds",
                    "element_label", "element_description"])
        for e, dmi, ds in zip(result.episodes, inter_mi, inter_s):
            label, description = metadata.get((e.layer, e.element), ("", ""))
            w.writerow([e.index, e.type, e.layer, e.element,
                        f"{e.start_mileage:.3f}", f"{e.end_mileage:.3f}",
                        f"{e.start_time_seconds:.1f}",
                        f"{e.end_time_seconds:.1f}",
                        f"{e.duration_seconds:.1f}",
                        f"{e.duration_miles:.3f}",
                        int(e.truncated), f"{dmi:.3f}", f"{ds:.1f}",
                        label, description])


def write_windows_csv(path, ws):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["window_index", "start_mile", "end_mile",
                    "episode_start_count"])
        for i, c in enumerate(ws["counts"]):
            w.writerow([i, f"{i * ws['window_miles']:.0f}",
                        f"{(i + 1) * ws['window_miles']:.0f}", c])


def _dist_stats(arr):
    arr = np.asarray(arr, dtype=float)
    return {"mean": float(arr.mean()), "median": float(np.median(arr)),
            "p90": float(np.percentile(arr, 90)),
            "min": float(arr.min()), "max": float(arr.max())}


def build_element_rarity_composition(result):
    """Exact element counts and achieved rarity proportions for one run."""
    layers = []
    for stats in result.layer_stats:
        total = stats["n_elements"]
        counts = {rarity: int(stats["counts"][rarity]) for rarity in RARITIES}
        layers.append({
            "layer": stats["layer"],
            "construction_mode": stats["construction_mode"],
            "total_elements": total,
            "counts": counts,
            "proportions": {
                rarity: counts[rarity] / total for rarity in RARITIES
            },
        })

    def aggregate(rows):
        counts = {
            rarity: sum(row["counts"][rarity] for row in rows)
            for rarity in RARITIES
        }
        total = sum(counts.values())
        return {
            "total_elements": total,
            "counts": counts,
            "proportions": {
                rarity: counts[rarity] / total if total else 0.0
                for rarity in RARITIES
            },
        }

    return {
        "configured_element_class_percentages": {
            rarity: float(result.config.element_class_percentages[rarity])
            for rarity in RARITIES
        },
        "configured_selection_class_percentages": {
            rarity: float(result.config.selection_class_percentages[rarity])
            for rarity in RARITIES
        },
        "allocation_method": "largest_remainder",
        "layers": layers,
        "all_layers_total": aggregate(layers),
    }


def build_summary(result, inter_mi, inter_s, ws, wall_seconds):
    cfg = result.config
    eps = result.episodes
    n = len(eps)
    dur_s = [e.duration_seconds for e in eps]
    dur_mi = [e.duration_miles for e in eps]
    n_trunc = sum(1 for e in eps if e.truncated)

    L = []
    L.append(f"# Layered Scenario Simulation - {cfg.profile_name}\n")
    L.append("## Run parameters\n")
    L.append(f"- simulator profile: `{cfg.profile_name}` "
             f"(`{cfg.profile_kind}`)")
    L.append(f"- target simulated time: {cfg.target_time_seconds / 3600:,.0f} "
             f"hours (default v6 target: 20,000 h)")
    L.append(f"- mileage is derived at {cfg.average_speed_mph} mph constant "
             "average speed; it is not the stopping criterion")
    L.append(f"- seeds: {json.dumps(cfg.seeds)}")
    tms = result.transition_model_stats
    L.append(f"- transition model: {tms['mode']}")
    if tms["mode"] == "conditional":
        L.append("- conditional initialization: "
                 f"{'ENABLED' if tms['conditional_initialization'] else 'disabled'}")
        L.append("- conditional dependency order: "
                 + " -> ".join(tms["dependency_order"]))
    counts = cfg.unknown_scenarios["combination_counts"]
    L.append("- unknown scenarios: exact rare-element combinations; "
             + ", ".join(f"C{k}={counts[k]}" for k in (3, 4, 5, 6))
             + "; every rule includes triggering_conditions")
    L.append("- direct selection-class percentages: "
             + ", ".join(
                 f"{rarity}={cfg.selection_class_percentages[rarity]:g}%"
                 for rarity in RARITIES))
    L.append(f"- concentration_scale: {cfg.concentration_scale:,.0f}, "
             f"allow_self_transition: {cfg.allow_self_transition}\n")

    composition = build_element_rarity_composition(result)
    target = composition["configured_element_class_percentages"]
    L.append("## Element rarity composition\n")
    L.append("The configured target for every generated layer is "
             f"common {target['common']:g}%, rare {target['rare']:g}%, "
             f"unknown {target['unknown']:g}%. Integer counts use the "
             "largest-remainder method.\n")
    L.append("| layer | mode | total | common | rare | unknown | achieved "
             "common / rare / unknown |")
    L.append("|---|---|---:|---:|---:|---:|---|")
    for row in composition["layers"]:
        counts = row["counts"]
        props = row["proportions"]
        L.append(
            f"| {row['layer']} | {row['construction_mode']} | "
            f"{row['total_elements']} | {counts['common']} | "
            f"{counts['rare']} | {counts['unknown']} | "
            f"{props['common']:.2%} / {props['rare']:.2%} / "
            f"{props['unknown']:.2%} |")
    row = composition["all_layers_total"]
    counts = row["counts"]
    props = row["proportions"]
    L.append(
        f"| **All layers total** | aggregate | **{row['total_elements']}** | "
        f"**{counts['common']}** | **{counts['rare']}** | "
        f"**{counts['unknown']}** | **{props['common']:.2%} / "
        f"{props['rare']:.2%} / {props['unknown']:.2%}** |")
    L.append("")

    if tms["mode"] == "conditional":
        L.append("## Conditional-transition diagnostics\n")
        if tms["rules"]:
            for rule in tms["rules"]:
                L.append(
                    f"- `{rule['id']}` -> {rule['target_layer']}: "
                    f"{rule['match_count']:,} matches; "
                    f"{rule['influenced_transition_count']:,} influenced "
                    "transitions"
                    + ("; modifies unknown-rarity probabilities"
                       if rule["modifies_unknown"] else ""))
        else:
            L.append("- no conditional rules configured")
        if any(rule["modifies_unknown"] for rule in tms["rules"]):
            L.append("- WARNING: conditional rules modify unknown-rarity "
                     "probabilities; the configured class percentage is a "
                     "baseline construction target, "
                     "not a guaranteed conditional or overall rate.")
        L.append("")

    L.append("## Totals\n")
    L.append(f"- total simulated mileage: {result.total_miles:,.1f} miles")
    L.append(f"- total simulated time: {result.total_time_seconds:,.1f} s "
             f"({result.total_time_seconds / 3600:,.1f} h)")
    L.append(f"- event-driven steps: {result.total_events:,}")
    L.append(f"- wall-clock runtime: {wall_seconds:,.1f} s\n")

    bt = result.episodes_by_type()
    L.append("## Unknown episodes\n")
    L.append(f"- total unknown episodes: {n:,} "
             f"(of which truncated at simulation end: {n_trunc})")
    types = ("rare_combination",)
    L.append("- by type: " + ", ".join(
        f"{typ.replace('_', ' ')} {bt[typ]:,}" for typ in types))
    for typ in types:
        ds = [e.duration_seconds for e in eps if e.type == typ]
        if ds:
            s = _dist_stats(ds)
            L.append(f"  - {typ} durations (s): mean {s['mean']:,.1f}, "
                     f"median {s['median']:,.1f}, p90 {s['p90']:,.1f}, "
                     f"max {s['max']:,.1f}")
    L.append(f"- episodes per 1,000,000 miles: "
             f"{result.episodes_per_million_miles():,.2f}")
    L.append("- episodes by C-size: " + ", ".join(
        f"C{k}: {result.combination_stats['episodes_by_size'][k]:,}"
        for k in (3, 4, 5, 6)))
    L.append(f"- total time in unknown scenario (union of episodes): "
             f"{result.total_unknown_time_seconds:,.1f} s = "
             f"{result.unknown_time_fraction():.4%} of simulated time")
    if n:
        s_ds = _dist_stats(dur_s)
        s_dm = _dist_stats(dur_mi)
        s_im = _dist_stats(inter_mi)
        s_is = _dist_stats(inter_s)
        L.append("- episode duration (seconds): "
                 f"mean {s_ds['mean']:,.1f}, median {s_ds['median']:,.1f}, "
                 f"p90 {s_ds['p90']:,.1f}, max {s_ds['max']:,.1f}")
        L.append("- episode duration (miles): "
                 f"mean {s_dm['mean']:,.3f}, median {s_dm['median']:,.3f}, "
                 f"p90 {s_dm['p90']:,.3f}, max {s_dm['max']:,.3f}")
        L.append("- inter-arrival distance between episode starts (miles): "
                 f"mean {s_im['mean']:,.1f}, median {s_im['median']:,.1f}, "
                 f"p90 {s_im['p90']:,.1f}, max {s_im['max']:,.1f}")
        L.append("- inter-arrival time between episode starts (seconds): "
                 f"mean {s_is['mean']:,.1f}, median {s_is['median']:,.1f}, "
                 f"p90 {s_is['p90']:,.1f}, max {s_is['max']:,.1f}")
        L.append("  (first inter-arrival measured from the start of the "
                 "simulation; every episode's mileage/time position is in "
                 "episodes.csv)\n")

    L.append("## Episode starts per mileage window\n")
    L.append(f"- window size: {ws['window_miles']:,.0f} miles "
             f"({ws['n_windows']} complete windows; counts in windows.csv)")
    L.append(f"- empirical mean count per window: {ws['mean_count']:,.3f}")
    L.append(f"- empirical variance of count per window: "
             f"{ws['variance_count']:,.3f}")
    L.append(f"- dispersion index (variance / mean): "
             f"{ws['dispersion_index']:,.3f} "
             "(~1 = Poisson-like; episode STARTS are near-Poisson because "
             "each start is an independent rare transition, unlike the old "
             "per-tuple encounter counting)\n")

    L.append("## Per-layer statistics\n")
    L.append("| layer | elements | common/rare/unknown | configured unk. mass | "
             "transition unk. mass | empirical unk. "
             "selection | episodes | transitions | mean duration cfg/emp (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for st in result.layer_stats:
        c = st["counts"]
        L.append(
            f"| {st['layer']} (generated) | {st['n_elements']} | "
            f"{c['common']}/{c['rare']}/{c['unknown']} | "
            f"{st['designed_unknown_mass']:.4%} | "
            f"{st['realized_unknown_mass']:.4%} | "
            f"{st['empirical_unknown_rate']:.4%} | {st['episodes']:,} | "
            f"{st['transitions']:,} | "
            f"{st['mean_duration_config']:.0f}/"
            f"{st['mean_duration_empirical']:.1f} |")

    if tms["mode"] == "conditional":
        L.append("\n### Conditional occupancy and selection\n")
        L.append("| layer | baseline unknown mass | empirical unknown "
                 "occupancy | conditional unknown selection | matched / "
                 "unmatched contexts | influenced transitions |")
        L.append("|---|---|---|---|---|---|")
        for row in tms["layers"]:
            L.append(
                f"| {row['layer']} | {row['baseline_unknown_mass']:.4%} | "
                f"{row['empirical_unknown_occupancy']:.4%} | "
                f"{row['conditional_unknown_selection_rate']:.4%} | "
                f"{row['matched_context_transitions']:,} / "
                f"{row['unmatched_context_transitions']:,} | "
                f"{row['influenced_transitions']:,} |")

    L.append("\n## Verification against configured targets\n")
    unk_layers = [st for st in result.layer_stats if st["has_unknown"]]
    tot_trans = sum(st["transitions"] for st in unk_layers)
    tot_unk = sum(st["unknown_selected"] for st in unk_layers)
    overall = tot_unk / tot_trans if tot_trans else 0.0
    target_unknown = cfg.selection_class_percentages["unknown"] / 100.0
    if tms["mode"] == "conditional":
        L.append(f"- unknown-element selection rate across unknown-bearing "
                  f"layers: {overall:.4%} (baseline construction target "
                  f"{target_unknown:.2%}; conditional "
                  "rules may legitimately move the empirical rate)")
    else:
        L.append(f"- unknown-element selection rate across unknown-bearing "
                  f"layers: {overall:.4%} (design target "
                  f"{target_unknown:.2%}; permanent class mass is exact)")
    cs = result.combination_stats
    if cs["enabled"] and cs["rules"]:
        L.append("- selected exact combination rules: " + "; ".join(
                     f"{r['description']} (mass {r['mass']:.4%}, "
                     f"episodes {r['episodes']:,})" for r in cs["rules"]))
    street = result.layer_stats[0]
    tot_v = sum(street["visit_counts"])
    rows = sorted(zip(street["element_names"], street["visit_counts"],
                      street["transition_probs"]),
                  key=lambda x: -x[2])
    L.append("- street composition, empirical visit share vs configured "
             "probability (top 5): " + "; ".join(
                 f"{nm} {v / tot_v:.3%} vs {p:.1%}"
                 for nm, v, p in rows[:5]))
    L.append("- unknown-rarity elements do not independently create unknown "
             "episodes; they are excluded from exact rare-combination matches")
    exp_h = result.total_miles / cfg.average_speed_mph
    L.append(f"- time/mileage consistency: {result.total_miles:,.1f} mi / "
             f"{cfg.average_speed_mph} mph = {exp_h:,.1f} h expected, "
             f"{result.total_time_seconds / 3600:,.1f} h simulated.")
    return "\n".join(L) + "\n"


def build_stats_json(result, inter_mi, inter_s, ws, wall_seconds):
    eps = result.episodes
    return {
        "profile_name": result.config.profile_name,
        "profile_kind": result.config.profile_kind,
        "total_simulated_mileage": result.total_miles,
        "total_simulated_time_seconds": result.total_time_seconds,
        "total_events": result.total_events,
        "wall_seconds": wall_seconds,
        "total_unknown_episodes": len(eps),
        "episodes_truncated": sum(1 for e in eps if e.truncated),
        "episodes_per_million_miles": result.episodes_per_million_miles(),
        "total_unknown_time_seconds": result.total_unknown_time_seconds,
        "unknown_time_fraction": result.unknown_time_fraction(),
        "episode_duration_seconds":
            _dist_stats([e.duration_seconds for e in eps]) if eps else None,
        "episode_duration_miles":
            _dist_stats([e.duration_miles for e in eps]) if eps else None,
        "inter_arrival_miles": _dist_stats(inter_mi) if eps else None,
        "inter_arrival_seconds": _dist_stats(inter_s) if eps else None,
        "mileage_windows": {
            "window_miles": ws["window_miles"],
            "n_windows": ws["n_windows"],
            "empirical_mean_count_per_window": ws["mean_count"],
            "empirical_variance_count_per_window": ws["variance_count"],
            "dispersion_index": ws["dispersion_index"],
        },
        "episodes_by_type": result.episodes_by_type(),
        "combination_stats": result.combination_stats,
        "transition_model": result.transition_model_stats,
        "element_rarity_composition": build_element_rarity_composition(result),
        "seeds": result.config.seeds,
        "layer_stats": [{k: v for k, v in st.items()
                         if k not in ("visit_counts", "element_names",
                                      "element_labels",
                                      "element_descriptions",
                                      "transition_probs")}
                        for st in result.layer_stats],
        "street_composition": {
            "elements": result.layer_stats[0]["element_names"],
            "configured_probabilities":
                result.layer_stats[0]["transition_probs"],
            "empirical_visit_share": [
                v / max(sum(result.layer_stats[0]["visit_counts"]), 1)
                for v in result.layer_stats[0]["visit_counts"]],
        },
    }


def make_plots(result, inter_mi, ws, plots_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(plots_dir, exist_ok=True)
    eps = result.episodes
    cfg = result.config

    # 1. cumulative episodes vs mileage
    fig, ax = plt.subplots(figsize=(9, 5))
    if eps:
        miles = [e.start_mileage for e in eps]
        ax.step(miles, range(1, len(miles) + 1), where="post", lw=0.9)
    ax.set_xlabel("mileage (miles)")
    ax.set_ylabel("cumulative unknown episodes")
    ax.set_title(f"Cumulative unknown episodes over {result.total_miles:,.0f} miles")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "cumulative_episodes.png"), dpi=150)
    plt.close(fig)


    # 2. episode duration histogram, overlaid by type
    fig, ax = plt.subplots(figsize=(9, 5))
    if eps:
        colors = {"rare_combination": "tab:green"}
        all_d = np.asarray([e.duration_seconds for e in eps])
        bins = np.linspace(0.0, float(np.percentile(all_d, 99.5)), 80)
        for typ, col in colors.items():
            d = [e.duration_seconds for e in eps if e.type == typ]
            if d:
                ax.hist(d, bins=bins, color=col, alpha=0.55,
                        label=f"{typ} (n={len(d):,}, mean {np.mean(d):.0f}s)")
        ax.legend(fontsize=8)
    ax.set_yscale("log")
    ax.set_xlabel("episode duration (seconds)")
    ax.set_ylabel("count (log scale)")
    ax.set_title("Unknown-episode durations")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "episode_durations.png"), dpi=150)
    plt.close(fig)

    # 3. inter-arrival distances between episode starts
    fig, ax = plt.subplots(figsize=(9, 5))
    if inter_mi:
        arr = np.asarray(inter_mi)
        ax.hist(arr, bins=100, color="tab:blue", alpha=0.8)
        ax.axvline(arr.mean(), color="tab:red", ls="--",
                   label=f"mean = {arr.mean():.1f} mi")
        ax.legend()
    ax.set_yscale("log")
    ax.set_xlabel("inter-arrival distance between episode starts (miles)")
    ax.set_ylabel("count (log scale)")
    ax.set_title("Inter-arrival distances")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "inter_arrival_hist.png"), dpi=150)
    plt.close(fig)

    # 4. episode starts per mileage window
    fig, ax = plt.subplots(figsize=(10, 5))
    starts = [i * ws["window_miles"] for i in range(ws["n_windows"])]
    ax.bar(starts, ws["counts"], width=ws["window_miles"] * 0.95,
           align="edge", color="tab:blue", alpha=0.8)
    ax.axhline(ws["mean_count"], color="tab:red", ls="--",
               label=f"mean = {ws['mean_count']:.1f}  "
                     f"var = {ws['variance_count']:.1f}  "
                     f"dispersion = {ws['dispersion_index']:.2f}")
    ax.set_xlabel("mileage (miles)")
    ax.set_ylabel(f"episode starts per {ws['window_miles']:,.0f}-mile window")
    ax.set_title("Unknown-episode starts per fixed mileage window")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "window_counts.png"), dpi=150)
    plt.close(fig)

    # 5. per-layer: episodes and unknown selection rate vs target
    labels = [st["layer"].replace("_", "\n") for st in result.layer_stats]
    x = np.arange(len(labels))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.bar(x, [st["episodes"] for st in result.layer_stats], color="tab:blue")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_ylabel("unknown episodes")
    ax1.set_title("Episodes by layer")
    ax1.grid(alpha=0.3, axis="y")
    ax2.bar(x - 0.15, [st["realized_unknown_mass"] for st in result.layer_stats],
            0.3, label="configured transition mass")
    ax2.bar(x + 0.15, [st["empirical_unknown_rate"] for st in result.layer_stats],
            0.3, label="empirical selection rate")
    unknown_target = cfg.selection_class_percentages["unknown"] / 100.0
    ax2.axhline(unknown_target, color="tab:red", ls="--",
                label=f"target {unknown_target:.1%}")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel("unknown-element probability / rate")
    ax2.set_title(f"Unknown selection (c = {cfg.concentration_scale:,.0f})")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "per_layer_stats.png"), dpi=150)
    plt.close(fig)

    # 6. street composition: configured vs empirical
    st = result.layer_stats[0]
    tot_v = max(sum(st["visit_counts"]), 1)
    names = st["element_names"]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - 0.2, st["transition_probs"], 0.4, label="configured probability")
    ax.bar(x + 0.2, [v / tot_v for v in st["visit_counts"]], 0.4,
           label="empirical visit share")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("probability / share")
    ax.set_title("Street layer: route composition, configured vs simulated")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "street_composition.png"), dpi=150)
    plt.close(fig)


def _gamma_pdf_grid(shape, scale, x):
    """Gamma PDF without requiring SciPy."""
    log_pdf = ((shape - 1.0) * np.log(x) - x / scale
               - math.lgamma(shape) - shape * math.log(scale))
    return np.exp(log_pdf)


def _regularized_gamma_p(shape, value):
    """Regularized lower incomplete Gamma P(shape, value), SciPy-free."""
    if value <= 0.0:
        return 0.0
    epsilon = 1e-12
    tiny = 1e-300
    if value < shape + 1.0:
        total = term = 1.0 / shape
        augmented_shape = shape
        for _ in range(1, 300):
            augmented_shape += 1.0
            term *= value / augmented_shape
            total += term
            if abs(term) < abs(total) * epsilon:
                break
        result = total * math.exp(
            -value + shape * math.log(value) - math.lgamma(shape))
        return min(1.0, result)

    b = value + 1.0 - shape
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for index in range(1, 300):
        coefficient = -index * (index - shape)
        b += 2.0
        d = coefficient * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + coefficient / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            break
    upper = math.exp(
        -value + shape * math.log(value) - math.lgamma(shape)) * h
    return max(0.0, min(1.0, 1.0 - upper))


def _gamma_cdf_grid(shape, scale, x):
    return np.asarray([
        _regularized_gamma_p(shape, value / scale) for value in x])


def make_duration_distribution_plots(result, output_dir):
    """Write one representative element-duration PDF/CDF figure per layer.

    Each figure contains the central common, rare, and unknown element when
    those rarities exist in the layer. Curves show the theoretical Gamma law
    before the configured minimum-duration clamp is applied.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(output_dir, exist_ok=True)
    colors = {"common": "tab:blue", "rare": "tab:orange",
              "unknown": "tab:green"}
    line_styles = {"common": "-", "rare": "--", "unknown": ":"}
    manifest = {
        "description": (
            "Representative per-layer Gamma duration distributions. Curves "
            "are theoretical before min_duration_seconds clamping."),
        "min_duration_seconds": result.config.min_duration_seconds,
        "selection": "element nearest the median configured mean per rarity",
        "layers": [],
    }

    for layer in result.layer_stats:
        selected = []
        for rarity in RARITIES:
            candidates = [element for element in layer["elements"]
                          if element["rarity"] == rarity]
            if not candidates:
                continue
            band_center = float(np.median(
                [element["duration_mean_seconds"] for element in candidates]))
            element = min(
                candidates,
                key=lambda value: (
                    abs(value["duration_mean_seconds"] - band_center),
                    value["id"]))
            selected.append(element)

        max_seconds = max(
            element["duration_mean_seconds"]
            + 6.0 * math.sqrt(element["duration_variance_seconds2"])
            for element in selected)
        x = np.linspace(max(1e-6, max_seconds / 10_000.0),
                        max_seconds, 1_200)
        fig, (ax_pdf, ax_cdf) = plt.subplots(1, 2, figsize=(13, 5))

        manifest_elements = []
        for element in selected:
            rarity = element["rarity"]
            mean = element["duration_mean_seconds"]
            shape = element["duration_gamma_shape"]
            scale = element["duration_gamma_scale"]
            pdf = _gamma_pdf_grid(shape, scale, x)
            cdf = _gamma_cdf_grid(shape, scale, x)
            label = f"{element['label']} ({rarity}, mean {mean:.2f} s)"
            style = dict(color=colors[rarity], linestyle=line_styles[rarity],
                         linewidth=2.0, label=label)
            ax_pdf.plot(x, pdf, **style)
            ax_cdf.plot(x, cdf, **style)
            ax_pdf.axvline(mean, color=colors[rarity], alpha=0.25,
                           linewidth=1.0)
            ax_cdf.axvline(mean, color=colors[rarity], alpha=0.25,
                           linewidth=1.0)
            manifest_elements.append({
                "id": element["id"],
                "label": element["label"],
                "rarity": rarity,
                "mean_seconds": mean,
                "variance_seconds2": element["duration_variance_seconds2"],
                "gamma_shape": shape,
                "gamma_scale": scale,
            })

        clamp = result.config.min_duration_seconds
        for axis in (ax_pdf, ax_cdf):
            axis.axvline(clamp, color="0.4", linestyle="-.", linewidth=1.0,
                        label=f"minimum clamp ({clamp:g} s)")
            axis.set_xlabel("duration (seconds)")
            axis.grid(alpha=0.25)
        ax_pdf.set_ylabel("probability density")
        ax_pdf.set_title("Gamma probability density")
        ax_cdf.set_ylabel("cumulative probability")
        ax_cdf.set_ylim(0.0, 1.02)
        ax_cdf.set_title("Gamma cumulative distribution")
        ax_pdf.legend(fontsize=8)
        ax_cdf.legend(fontsize=8)
        layer_title = layer["layer"].replace("_", " ").title()
        fig.suptitle(f"{layer_title}: representative element durations")
        fig.tight_layout()
        filename = f"{layer['layer']}.png"
        fig.savefig(os.path.join(output_dir, filename), dpi=150)
        plt.close(fig)
        manifest["layers"].append({
            "layer": layer["layer"],
            "file": filename,
            "elements": manifest_elements,
        })

    with open(os.path.join(output_dir, "manifest.json"), "w",
              encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--max-wall-seconds", type=float, default=None)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.checkpoint and os.path.exists(args.checkpoint):
        with open(args.checkpoint, "rb") as f:
            sim, state = pickle.load(f)
        cfg = sim.cfg
        print(f"resumed checkpoint: {state['t'] / 3600:,.1f} / "
              f"{cfg.target_time_seconds / 3600:,.1f} simulated hours, "
              f"{state['events']:,} events, "
              f"{state['episodes_opened']:,} episodes so far")
    else:
        cfg = SimConfig.from_yaml(args.config)
        print(f"config: {args.config}")
        print(f"profile: {cfg.profile_name} ({cfg.profile_kind})")
        print(f"seeds: {cfg.seeds}")
        sim = ScenarioSimulator(cfg)
        state = None
        for layer in sim.layers:
            unk = sum(layer.is_unknown)
            print(f"layer {layer.key:26s} n={layer.n_elements:3d} "
                  f"generated=true unknown_elements={unk} "
                  f"realized_unknown_mass={layer.realized_unknown_mass():.4%}")

    result, state = sim.run_resumable(
        state=state, wall_limit_seconds=args.max_wall_seconds,
        progress_every_miles=100_000, log=print)

    if result is None:
        with open(args.checkpoint, "wb") as f:
            pickle.dump((sim, state), f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"checkpoint saved: {state['t'] / 3600:,.1f} / "
              f"{cfg.target_time_seconds / 3600:,.1f} simulated hours "
              f"({state['t'] / cfg.target_time_seconds:.1%})")
        sys.exit(3)

    if args.checkpoint and os.path.exists(args.checkpoint):
        os.remove(args.checkpoint)
    wall = state["wall_seconds"]
    print(f"simulation finished: {result.total_time_seconds / 3600:,.1f} "
          f"simulated hours ({result.total_miles:,.1f} derived miles), "
          f"{result.total_events:,} events, {len(result.episodes):,} "
          f"unknown episodes, {wall:,.1f} s wall time")

    inter_mi = result.inter_arrival_miles()
    inter_s = result.inter_arrival_seconds()
    ws = result.window_stats()
    write_episodes_csv(os.path.join(args.outdir, "episodes.csv"),
                       result, inter_mi, inter_s)
    write_windows_csv(os.path.join(args.outdir, "windows.csv"), ws)
    with open(os.path.join(args.outdir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(build_summary(result, inter_mi, inter_s, ws, wall))
    with open(os.path.join(args.outdir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(build_stats_json(result, inter_mi, inter_s, ws, wall),
                  f, indent=2)
    if not args.no_plots:
        make_plots(result, inter_mi, ws, os.path.join(args.outdir, "plots"))
        make_duration_distribution_plots(
            result, os.path.join(args.outdir, "duration_distributions"))
    print(f"results written to {args.outdir}/")


if __name__ == "__main__":
    main()
