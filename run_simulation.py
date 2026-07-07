#!/usr/bin/env python3
"""Run the layered scenario simulation and write results.

Outputs (in --outdir):
  encounters.csv   one row per unknown-scenario encounter
  summary.md       human-readable results summary + verification
  stats.json       machine-readable statistics
  plots/*.png      cumulative encounters, inter-arrival histogram,
                   per-layer unknown rates, rarity selection shares
"""

import argparse
import csv
import json
import os
import pickle
import sys
import time

import numpy as np

from simulator import (LAYER_DEFINITIONS, RARITIES, ScenarioSimulator,
                       SimConfig)


def write_encounters_csv(path, result, inter):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["encounter_index", "mileage_miles", "time_seconds",
                    "time_hours", "reason", "inter_arrival_miles", "scenario"])
        for e, d in zip(result.encounters, inter):
            w.writerow([e.index, f"{e.mileage:.3f}", f"{e.time_seconds:.1f}",
                        f"{e.time_seconds / 3600:.3f}", e.reason,
                        f"{d:.3f}", e.scenario])


def build_summary(result, inter, wall_seconds):
    cfg = result.config
    enc = result.encounters
    n = len(enc)
    by_reason = {"unknown_element": 0, "unknown_combination": 0}
    for e in enc:
        by_reason[e.reason] += 1

    lines = []
    lines.append("# Layered Scenario Simulation - Results Summary\n")
    lines.append("## Run parameters\n")
    lines.append(f"- target mileage: {cfg.target_total_miles:,.0f} miles at "
                 f"{cfg.average_speed_mph} mph constant average speed")
    lines.append(f"- simulation_seed: {cfg.simulation_seed}, global_seed: {cfg.global_seed}")
    lines.append(f"- unknown_weight_mode: {cfg.unknown_weight_mode} "
                 f"(target_unknown_element_probability = {cfg.target_unknown_element_probability})")
    lines.append(f"- unknown_combination_probability: {cfg.unknown_combination_probability}")
    lines.append(f"- concentration_scale: {cfg.concentration_scale}, "
                 f"allow_self_transition: {cfg.allow_self_transition}\n")

    lines.append("## Totals\n")
    lines.append(f"- simulated distance: {result.total_miles:,.1f} miles")
    lines.append(f"- simulated time: {result.total_time_seconds:,.0f} s "
                 f"({result.total_time_seconds / 3600:,.1f} h)")
    lines.append(f"- event-driven steps: {result.total_events:,}")
    lines.append(f"- scenario tuple changes: {result.total_tuple_changes:,}")
    lines.append(f"- wall-clock runtime: {wall_seconds:,.1f} s\n")

    lines.append("## Unknown scenario encounters\n")
    lines.append(f"- total encounters: {n:,}")
    lines.append(f"  - via unknown element: {by_reason['unknown_element']:,}")
    lines.append(f"  - via unknown combination (hash): {by_reason['unknown_combination']:,}")
    if result.total_miles > 0:
        lines.append(f"- encounters per 1,000,000 miles: "
                     f"{n / (result.total_miles / 1e6):,.1f}")
    if n:
        arr = np.asarray(inter)
        lines.append(f"- first encounter at mile {enc[0].mileage:,.2f}, "
                     f"last at mile {enc[-1].mileage:,.2f}")
        lines.append("- inter-arrival distance (miles): "
                     f"mean {arr.mean():,.3f}, median {np.median(arr):,.3f}, "
                     f"p90 {np.percentile(arr, 90):,.3f}, "
                     f"min {arr.min():,.3f}, max {arr.max():,.3f}")
        lines.append("  (first inter-arrival = distance from start to first "
                     "encounter; full list in encounters.csv)\n")

    lines.append("## Per-layer statistics\n")
    header = ("| layer | elements | common/medium/rare/very_rare/unknown | "
              "unknown_weight | designed unk. mass | realized unk. mass "
              "(Dirichlet) | empirical unk. selection rate | transitions | "
              "mean duration cfg/emp (s) |")
    lines.append(header)
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for st in result.layer_stats:
        c = st["counts"]
        lines.append(
            f"| {st['layer']} | {st['n_elements']} | "
            f"{c['common']}/{c['medium']}/{c['rare']}/{c['very_rare']}/{c['unknown']} | "
            f"{st['unknown_weight']:.5f} | {st['designed_unknown_mass']:.4%} | "
            f"{st['realized_unknown_mass']:.4%} | "
            f"{st['empirical_unknown_rate']:.4%} | {st['transitions']:,} | "
            f"{st['mean_duration_config']:.0f}/{st['mean_duration_empirical']:.1f} |")

    lines.append("\n## Verification against configured targets\n")
    tot_trans = sum(st["transitions"] for st in result.layer_stats)
    tot_unk = sum(st["unknown_selected"] for st in result.layer_stats)
    overall = tot_unk / tot_trans if tot_trans else 0.0
    lines.append(f"- overall unknown-element selection rate across all "
                 f"transitions: {overall:.4%} "
                 f"(design target {cfg.target_unknown_element_probability:.2%}; "
                 "per-layer rates scatter around the target because each "
                 "layer's transition vector is a single Dirichlet draw with "
                 f"concentration_scale={cfg.concentration_scale} - increase "
                 "concentration_scale for tighter adherence)")
    if result.known_tuple_changes:
        comb_rate = by_reason["unknown_combination"] / result.known_tuple_changes
        lines.append(f"- unknown-combination rate among all-known tuple changes: "
                     f"{comb_rate:.4%} "
                     f"(target {cfg.unknown_combination_probability:.2%})")
    lines.append("- empirical mean durations per layer are listed above and "
                 "should be close to the configured means (Gamma "
                 "parameterization: shape = mean^2/var, scale = var/mean).")
    exp_time_h = result.total_miles / cfg.average_speed_mph
    lines.append(f"- time/mileage consistency: {result.total_miles:,.1f} mi / "
                 f"{cfg.average_speed_mph} mph = {exp_time_h:,.1f} h expected, "
                 f"{result.total_time_seconds / 3600:,.1f} h simulated.")
    return "\n".join(lines) + "\n"


def build_stats_json(result, inter, wall_seconds):
    enc = result.encounters
    by_reason = {"unknown_element": 0, "unknown_combination": 0}
    for e in enc:
        by_reason[e.reason] += 1
    arr = np.asarray(inter) if enc else np.asarray([0.0])
    return {
        "total_miles": result.total_miles,
        "total_time_seconds": result.total_time_seconds,
        "total_events": result.total_events,
        "total_tuple_changes": result.total_tuple_changes,
        "known_tuple_changes": result.known_tuple_changes,
        "wall_seconds": wall_seconds,
        "encounters_total": len(enc),
        "encounters_by_reason": by_reason,
        "encounters_per_million_miles":
            len(enc) / (result.total_miles / 1e6) if result.total_miles else 0.0,
        "inter_arrival_miles": {
            "mean": float(arr.mean()), "median": float(np.median(arr)),
            "p90": float(np.percentile(arr, 90)),
            "min": float(arr.min()), "max": float(arr.max()),
        } if enc else None,
        "layer_stats": result.layer_stats,
    }


def make_plots(result, inter, sim, plots_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(plots_dir, exist_ok=True)
    enc = result.encounters
    cfg = result.config

    # 1. cumulative encounters vs mileage
    fig, ax = plt.subplots(figsize=(9, 5))
    if enc:
        miles = [e.mileage for e in enc]
        ax.step(miles, range(1, len(miles) + 1), where="post", lw=0.9)
    ax.set_xlabel("mileage (miles)")
    ax.set_ylabel("cumulative unknown-scenario encounters")
    ax.set_title(f"Cumulative unknown encounters over {result.total_miles:,.0f} miles")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "cumulative_encounters.png"), dpi=150)
    plt.close(fig)

    # 2. inter-arrival distance histogram (log y)
    fig, ax = plt.subplots(figsize=(9, 5))
    if inter:
        arr = np.asarray(inter)
        ax.hist(arr, bins=100, color="tab:blue", alpha=0.8)
        ax.axvline(arr.mean(), color="tab:red", ls="--",
                   label=f"mean = {arr.mean():.2f} mi")
        ax.legend()
    ax.set_yscale("log")
    ax.set_xlabel("inter-arrival distance between encounters (miles)")
    ax.set_ylabel("count (log scale)")
    ax.set_title("Distribution of inter-arrival distances")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "inter_arrival_hist.png"), dpi=150)
    plt.close(fig)

    # 3. per-layer unknown-selection rate: designed vs realized vs empirical
    labels = [st["layer"].replace("_", "\n") for st in result.layer_stats]
    designed = [st["designed_unknown_mass"] for st in result.layer_stats]
    realized = [st["realized_unknown_mass"] for st in result.layer_stats]
    empirical = [st["empirical_unknown_rate"] for st in result.layer_stats]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - 0.25, designed, 0.25, label="designed weight mass")
    ax.bar(x, realized, 0.25, label="realized Dirichlet mass")
    ax.bar(x + 0.25, empirical, 0.25, label="empirical selection rate")
    ax.axhline(cfg.target_unknown_element_probability, color="tab:red", ls="--",
               label=f"target = {cfg.target_unknown_element_probability:.2%}")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("unknown-element probability / rate")
    ax.set_title("Unknown-element selection per layer "
                 f"(concentration_scale = {cfg.concentration_scale})")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "unknown_rates_per_layer.png"), dpi=150)
    plt.close(fig)

    # 4. aggregate rarity selection share: realized vector mass vs empirical
    realized_mass = dict.fromkeys(RARITIES, 0.0)
    for layer in sim.layers:
        m = layer.rarity_mass(layer.transition_probs)
        for r in RARITIES:
            realized_mass[r] += m[r] / len(sim.layers)
    tot_sel = sum(sum(st["selected_by_rarity"].values())
                  for st in result.layer_stats)
    empirical_share = {
        r: sum(st["selected_by_rarity"][r] for st in result.layer_stats) / tot_sel
        for r in RARITIES}
    x = np.arange(len(RARITIES))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.2, [realized_mass[r] for r in RARITIES], 0.4,
           label="expected (avg realized vector mass)")
    ax.bar(x + 0.2, [empirical_share[r] for r in RARITIES], 0.4,
           label="empirical selection share")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(RARITIES)
    ax.set_ylabel("selection share (log scale)")
    ax.set_title("Selection share by rarity category (all layers aggregated)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(plots_dir, "rarity_selection_share.png"), dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--checkpoint", default=None,
                    help="checkpoint file for chunked execution")
    ap.add_argument("--max-wall-seconds", type=float, default=None,
                    help="stop after this many wall-clock seconds and save a "
                         "checkpoint; rerun with the same --checkpoint to "
                         "resume (results are bit-identical to a single run)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    if args.checkpoint and os.path.exists(args.checkpoint):
        with open(args.checkpoint, "rb") as f:
            sim, state = pickle.load(f)
        cfg = sim.cfg
        print(f"resumed checkpoint: {state['miles']:,.0f} miles, "
              f"{state['events']:,} events, "
              f"{len(state['encounters']):,} encounters so far")
    else:
        cfg = SimConfig.from_yaml(args.config)
        print(f"config: {args.config}")
        sim = ScenarioSimulator(cfg)
        state = None
        for layer in sim.layers:
            print(f"layer {layer.key:26s} n={layer.n_elements:3d} "
                  f"counts={layer.counts} unknown_weight={layer.unknown_weight:.5f} "
                  f"realized_unknown_mass={layer.realized_unknown_mass():.4%}")

    result, state = sim.run_resumable(
        state=state, wall_limit_seconds=args.max_wall_seconds,
        progress_every_miles=100_000, log=print)

    if result is None:
        with open(args.checkpoint, "wb") as f:
            pickle.dump((sim, state), f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"checkpoint saved: {state['miles']:,.0f} / "
              f"{cfg.target_total_miles:,.0f} miles "
              f"({state['miles'] / cfg.target_total_miles:.1%}), "
              f"{state['wall_seconds']:,.0f} s total wall time")
        sys.exit(3)  # not finished yet

    if args.checkpoint and os.path.exists(args.checkpoint):
        os.remove(args.checkpoint)
    wall = state["wall_seconds"]
    print(f"simulation finished: {result.total_miles:,.1f} miles, "
          f"{result.total_events:,} events, {len(result.encounters):,} "
          f"unknown encounters, {wall:,.1f} s wall time")

    inter = result.inter_arrival_miles()
    write_encounters_csv(os.path.join(args.outdir, "encounters.csv"), result, inter)
    with open(os.path.join(args.outdir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(build_summary(result, inter, wall))
    with open(os.path.join(args.outdir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(build_stats_json(result, inter, wall), f, indent=2)
    if not args.no_plots:
        make_plots(result, inter, sim, os.path.join(args.outdir, "plots"))
    print(f"results written to {args.outdir}/")


if __name__ == "__main__":
    main()
