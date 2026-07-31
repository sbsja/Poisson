"""One-at-a-time (OAT) parameter-sensitivity study for the AV scenario simulator.

Goal
----
Determine which configuration parameters move the simulator's outputs and how,
and---equally important---which parameters do NOT move the outputs beyond the
natural run-to-run noise of the model.

Design
------
* Every parameter is varied ONE AT A TIME from the delivered ``config.yaml``
  baseline; all other settings are held fixed.
* Every variant (including the untouched baseline) is run for ``REPLICATES``
  independent seed sets.  A replicate offsets ALL random streams---the seven
  construction/runtime seeds AND the full-scenario ``calibration_seed``---so a
  replicate is a genuinely independent history of the whole model.
* The baseline's spread across those replicates is the **seed-only noise band**:
  the negative control.  Every parameter's effect is reported both in absolute
  units and as a signal-to-noise ratio = (effect range across the swept levels)
  / (baseline seed standard deviation).  NO significance cut-off is baked in:
  the ranking is presented so the threshold can be chosen later from the data.
* Every run is a full ``target_total_miles`` history (2,000,000 miles by
  default), matching production fidelity.

Runs are independent and dispatched across processes.  Each worker writes a
compact ``stats.json`` for provenance and returns only scalar metrics.

Usage
-----
    python run_study.py                       # full study, full mileage
    python run_study.py --workers 12
    python run_study.py --dry-run             # list variants, run nothing
    python run_study.py --miles 200000 --replicates 2   # fast smoke test
    python run_study.py --factors average_speed_mph concentration_scale
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDY_DIR.parents[1]
RESULTS_DIR = STUDY_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

sys.path.insert(0, str(PROJECT_ROOT))

from simulator import ScenarioSimulator, SimConfig  # noqa: E402
from run_simulation import build_stats_json  # noqa: E402

# All seven simulator seeds plus the full-scenario calibration seed are shifted
# together for each replicate, so a replicate is an independent whole-model
# history and the baseline spread captures every source of model randomness.
SEED_STEP = 1_000_003
BASELINE_LABEL = "baseline"
BASELINE_FACTOR = "_baseline_"

# Headline metrics extracted from each run's stats.json.  "lower/higher good"
# is not implied---these are descriptive outputs, not objectives.
METRIC_KEYS = (
    "episodes_per_million_miles",
    "unknown_time_fraction",
    "total_unknown_episodes",
    "total_events",
    "duration_s_mean",
    "duration_s_median",
    "duration_s_p90",
    "duration_mi_mean",
    "inter_arrival_mi_mean",
    "inter_arrival_s_mean",
    "dispersion_index",
    "episodes_element",
    "episodes_hidden_triggering",
    "episodes_full_scenario",
)
# The two primary outputs the study ranks parameters against.
PRIMARY_METRICS = ("episodes_per_million_miles", "unknown_time_fraction")


# ==========================================================================
# Mutation specs -- plain data so they pickle across the spawn boundary.
# apply_mutation() interprets a spec against a fresh SimConfig in each worker.
# ==========================================================================
def apply_mutation(cfg: SimConfig, spec: dict) -> None:
    kind = spec["kind"]
    if kind == "baseline":
        return
    if kind == "attr":
        setattr(cfg, spec["name"], spec["value"])
    elif kind == "dict_attr":
        current = dict(getattr(cfg, spec["name"]))
        current[spec["key"]] = spec["value"]
        setattr(cfg, spec["name"], current)
    elif kind == "layer_field":
        setattr(cfg.layers[spec["layer"]], spec["field"], spec["value"])
    elif kind == "layer_count":
        lp = cfg.layers[spec["layer"]]
        lp.element_count_min = spec["value"]
        lp.element_count_max = spec["value"]
    elif kind == "replace_attr":
        setattr(cfg, spec["name"], deepcopy(spec["value"]))
    elif kind == "multi":
        for op in spec["ops"]:
            apply_mutation(cfg, op)
    else:  # pragma: no cover - guarded by build-time construction
        raise ValueError(f"unknown mutation kind: {kind}")


def offset_seeds(cfg: SimConfig, replicate: int) -> None:
    delta = replicate * SEED_STEP
    cfg.seeds = {k: v + delta for k, v in cfg.seeds.items()}
    fs = dict(cfg.full_scenario_unknowns)
    fs["calibration_seed"] = int(fs["calibration_seed"]) + delta
    cfg.full_scenario_unknowns = fs


# ==========================================================================
# Worker -- one full simulation history; returns scalar metrics only.
# ==========================================================================
def run_task(task: dict) -> dict:
    factor = task["factor"]
    level = task["level"]
    replicate = task["replicate"]
    row = {
        "factor": factor,
        "level": level,
        "level_value": task["level_value"],
        "replicate": replicate,
        "feasible": True,
        "error": None,
    }
    for key in METRIC_KEYS:
        row[key] = None
    row["wall_seconds"] = None

    try:
        cfg = SimConfig.from_yaml(str(CONFIG_PATH))
        cfg.target_total_miles = float(task["miles"])
        apply_mutation(cfg, task["spec"])
        offset_seeds(cfg, replicate)
        cfg.validate()

        started = time.monotonic()
        result = ScenarioSimulator(cfg).run()
        wall = time.monotonic() - started

        inter_mi = result.inter_arrival_miles()
        inter_s = result.inter_arrival_seconds()
        ws = result.window_stats()
        stats = build_stats_json(result, inter_mi, inter_s, ws, wall)
    except Exception as exc:  # infeasible config or run failure -> record it
        row["feasible"] = False
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    dur_s = stats["episode_duration_seconds"] or {}
    dur_mi = stats["episode_duration_miles"] or {}
    ia_mi = stats["inter_arrival_miles"] or {}
    ia_s = stats["inter_arrival_seconds"] or {}
    by_type = stats["episodes_by_type"]
    row.update({
        "episodes_per_million_miles": stats["episodes_per_million_miles"],
        "unknown_time_fraction": stats["unknown_time_fraction"],
        "total_unknown_episodes": stats["total_unknown_episodes"],
        "total_events": stats["total_events"],
        "duration_s_mean": dur_s.get("mean"),
        "duration_s_median": dur_s.get("median"),
        "duration_s_p90": dur_s.get("p90"),
        "duration_mi_mean": dur_mi.get("mean"),
        "inter_arrival_mi_mean": ia_mi.get("mean"),
        "inter_arrival_s_mean": ia_s.get("mean"),
        "dispersion_index": stats["mileage_windows"]["dispersion_index"],
        "episodes_element": by_type.get("element", 0),
        "episodes_hidden_triggering": by_type.get("hidden_triggering_unknown", 0),
        "episodes_full_scenario": by_type.get("full_scenario", 0),
        "wall_seconds": wall,
    })

    run_dir = RUNS_DIR / factor / level / f"replicate_{replicate + 1}"
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    return row


# ==========================================================================
# Variant construction -- every non-baseline variant changes ONE factor.
# level_value is the numeric level for trend analysis (None for categorical).
# ==========================================================================
def build_variants(cfg: SimConfig) -> list:
    """Return [(factor, level_label, level_value, spec), ...] excluding baseline.

    Baseline layer values are read from ``cfg`` so per-layer sweeps are relative.
    """
    variants = []

    def add(factor, level, value, spec):
        variants.append((factor, level, value, spec))

    # --- Global physics ---------------------------------------------------
    for v in (25.0, 75.0, 100.0):                       # baseline 50
        add("average_speed_mph", f"{v:g}", v,
            {"kind": "attr", "name": "average_speed_mph", "value": v})

    for v in (0.001, 0.5, 5.0, 30.0):                   # baseline 1.0
        add("min_duration_seconds", f"{v:g}", v,
            {"kind": "attr", "name": "min_duration_seconds", "value": v})

    # --- Unknown-element weighting ---------------------------------------
    for v in (0.001, 0.002, 0.008, 0.016):              # baseline 0.004
        add("target_unknown_element_probability", f"{v:g}", v,
            {"kind": "attr",
             "name": "target_unknown_element_probability", "value": v})

    for v in (0.0005, 0.001, 0.005):                    # only active in fixed mode
        add("fixed_unknown_weight", f"fixed_{v:g}", v,
            {"kind": "multi", "ops": [
                {"kind": "attr", "name": "unknown_weight_mode", "value": "fixed"},
                {"kind": "attr", "name": "fixed_unknown_weight", "value": v},
            ]})

    for v in (1000.0, 5000.0, 100000.0):                # baseline 20000
        add("concentration_scale", f"{v:g}", v,
            {"kind": "attr", "name": "concentration_scale", "value": v})

    # --- Rarity structure -------------------------------------------------
    # Alternative known-mass shapes (unknown share held at 0.10 for comparability).
    proportion_presets = {
        "common_heavy": {"common": 0.70, "medium": 0.13, "rare": 0.05,
                         "very_rare": 0.02, "unknown": 0.10},
        "tail_heavy":   {"common": 0.30, "medium": 0.25, "rare": 0.20,
                         "very_rare": 0.15, "unknown": 0.10},
        "flat_known":   {"common": 0.225, "medium": 0.225, "rare": 0.225,
                         "very_rare": 0.225, "unknown": 0.10},
    }
    for label, props in proportion_presets.items():
        add("rarity_proportions_shape", label, None,
            {"kind": "replace_attr", "name": "rarity_proportions",
             "value": props})

    # Unknown share swept (known mass renormalised to keep the sum at 1).
    for u in (0.05, 0.20):                              # baseline 0.10
        known = {"common": 0.50, "medium": 0.25, "rare": 0.10, "very_rare": 0.05}
        scale = (1.0 - u) / sum(known.values())
        props = {k: v * scale for k, v in known.items()}
        props["unknown"] = u
        add("unknown_proportion", f"{u:g}", u,
            {"kind": "replace_attr", "name": "rarity_proportions",
             "value": props})

    base_weight_presets = {
        "flatter": {"common": 1.0, "medium": 0.6, "rare": 0.3, "very_rare": 0.15},
        "steeper": {"common": 1.0, "medium": 0.2, "rare": 0.03, "very_rare": 0.008},
    }
    for label, weights in base_weight_presets.items():
        add("base_weights_shape", label, None,
            {"kind": "replace_attr", "name": "base_weights", "value": weights})

    # --- Full-scenario & hidden-triggering routes ------------------------
    for v in (0.002, 0.008):                            # baseline 0.004
        add("full_scenario_target_mass", f"{v:g}", v,
            {"kind": "dict_attr", "name": "full_scenario_unknowns",
             "key": "target_stationary_mass", "value": v})
    add("full_scenario_enabled", "off", 0.0,
        {"kind": "dict_attr", "name": "full_scenario_unknowns",
         "key": "enabled", "value": False})
    add("hidden_triggering_enabled", "off", 0.0,
        {"kind": "attr", "name": "enable_hidden_triggering_unknowns",
         "value": False})

    # --- Per-layer durations (multiplicative around each layer's baseline) -
    for layer_key, lp in cfg.layers.items():
        base_mean = lp.mean_duration
        base_var = lp.variance_duration
        for mult in (0.5, 2.0):
            add(f"mean_duration.{layer_key}", f"x{mult:g}", mult,
                {"kind": "layer_field", "layer": layer_key,
                 "field": "mean_duration", "value": base_mean * mult})
        for mult in (0.25, 4.0):
            add(f"variance_duration.{layer_key}", f"x{mult:g}", mult,
                {"kind": "layer_field", "layer": layer_key,
                 "field": "variance_duration", "value": base_var * mult})

    # --- Per-layer element counts (pinned min==max) ----------------------
    # Infeasible pins (e.g. unknown-weight feasibility) are caught per-run and
    # reported, never silently dropped.
    element_count_levels = {
        "temporal_modifications": (30, 46),
        "ego_maneuver": (7, 12),
        "ru_maneuver": (7, 12),
        "environmental_conditions": (15, 21),
        "triggering_conditions": (50, 75, 100, 150),   # flagged TODO in config
    }
    for layer_key, counts in element_count_levels.items():
        for n in counts:
            add(f"element_count.{layer_key}", f"n{n}", float(n),
                {"kind": "layer_count", "layer": layer_key, "value": n})

    # --- Transition structure --------------------------------------------
    add("allow_self_transition", "off", 0.0,
        {"kind": "attr", "name": "allow_self_transition", "value": False})

    # Conditional mode is a STRUCTURAL variant, not a pure OAT knob: enabling it
    # requires disabling full_scenario_unknowns.  Compare its marginal effect
    # against the standalone 'full_scenario_enabled=off' variant above.
    conditional_model = {
        "mode": "conditional",
        "conditional": {
            "apply_to_initial_state": True,
            "rules": [{
                "id": "merge_affects_ego",
                "target_layer": "ego_maneuver",
                "when": {"street": {"elements": ["forced_merge_proceeding",
                                                 "forced_merge_merging"]}},
                "multipliers": {"rarities": {"rare": 1.5, "common": 0.7}},
            }],
        },
    }
    add("transition_mode_conditional", "conditional", None,
        {"kind": "multi", "ops": [
            {"kind": "dict_attr", "name": "full_scenario_unknowns",
             "key": "enabled", "value": False},
            {"kind": "replace_attr", "name": "transition_model",
             "value": conditional_model},
        ]})

    return variants


# ==========================================================================
# Aggregation & analysis
# ==========================================================================
def _mean(values):
    return statistics.fmean(values) if values else None


def _sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def aggregate(rows):
    """Aggregate per (factor, level): mean/sd/min/max/n for each metric."""
    groups = {}
    for row in rows:
        groups.setdefault((row["factor"], row["level"]), []).append(row)

    summary = []
    for (factor, level), group in groups.items():
        feasible = [r for r in group if r["feasible"]]
        entry = {
            "factor": factor,
            "level": level,
            "level_value": group[0]["level_value"],
            "replicates": len(group),
            "feasible_runs": len(feasible),
            "errors": len(group) - len(feasible),
            "error_example": next((r["error"] for r in group if r["error"]), None),
        }
        for metric in METRIC_KEYS:
            values = [r[metric] for r in feasible if r[metric] is not None]
            entry[f"{metric}_mean"] = _mean(values)
            entry[f"{metric}_sd"] = _sd(values) if values else None
            entry[f"{metric}_min"] = min(values) if values else None
            entry[f"{metric}_max"] = max(values) if values else None
        summary.append(entry)
    return summary


def _pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 2:
        return None
    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    mx, my = _mean(xs2), _mean(ys2)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs2))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys2))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _trend(level_values, means):
    """Describe direction of a numeric factor's response."""
    pairs = sorted(
        [(v, m) for v, m in zip(level_values, means)
         if v is not None and m is not None],
        key=lambda p: p[0],
    )
    if len(pairs) < 2:
        return "n/a"
    ys = [m for _, m in pairs]
    diffs = [b - a for a, b in zip(ys, ys[1:])]
    span = max(ys) - min(ys)
    ref = max(abs(y) for y in ys) or 1.0
    if span / ref < 1e-6:
        return "flat"
    up = all(d >= -1e-9 * ref for d in diffs)
    down = all(d <= 1e-9 * ref for d in diffs)
    if up:
        return "increasing"
    if down:
        return "decreasing"
    return "non-monotonic"


def rank_sensitivity(summary):
    """For each factor and each metric: effect range across its levels
    (baseline level included) and the signal-to-noise ratio against the
    baseline seed standard deviation.  No significance verdict is applied."""
    baseline = next(e for e in summary if e["factor"] == BASELINE_FACTOR)
    by_factor = {}
    for entry in summary:
        if entry["factor"] == BASELINE_FACTOR:
            continue
        by_factor.setdefault(entry["factor"], []).append(entry)

    ranking = []
    for factor, entries in by_factor.items():
        # The baseline run is the shared 'baseline' level of every factor.
        levels = entries + [baseline]
        record = {
            "factor": factor,
            "n_levels": len(levels),
            "any_infeasible": any(e["errors"] for e in entries),
        }
        for metric in METRIC_KEYS:
            means = [e[f"{metric}_mean"] for e in levels
                     if e[f"{metric}_mean"] is not None]
            base_mean = baseline[f"{metric}_mean"]
            base_sd = baseline[f"{metric}_sd"]
            if len(means) >= 2 and base_mean not in (None, 0):
                effect_range = max(means) - min(means)
                effect_pct = effect_range / abs(base_mean) * 100.0
                snr = (effect_range / base_sd) if base_sd else float("inf")
            else:
                effect_range = effect_pct = snr = None
            record[f"{metric}_effect_range"] = effect_range
            record[f"{metric}_effect_pct"] = effect_pct
            record[f"{metric}_snr"] = snr

            # trend for numeric factors
            numeric = [(e["level_value"], e[f"{metric}_mean"]) for e in levels
                       if e["level_value"] is not None]
            if numeric:
                lv = [n[0] for n in numeric]
                mv = [n[1] for n in numeric]
                record[f"{metric}_trend"] = _trend(lv, mv)
                record[f"{metric}_pearson"] = _pearson(lv, mv)
            else:
                record[f"{metric}_trend"] = "categorical"
                record[f"{metric}_pearson"] = None
        ranking.append(record)

    # Sort by the larger primary-metric SNR so the most influential float up.
    def key(rec):
        snrs = [rec[f"{m}_snr"] for m in PRIMARY_METRICS
                if rec[f"{m}_snr"] is not None]
        return max(snrs) if snrs else -1.0
    ranking.sort(key=key, reverse=True)
    return ranking, baseline


# ==========================================================================
# Output: CSV, plots, report
# ==========================================================================
def write_csv(path, rows):
    if not rows:
        return
    fieldnames = list(rows[0])
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_plots(summary, ranking, baseline):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1. Tornado charts: signal-to-noise per factor for each primary metric.
    fig, axes = plt.subplots(1, 2, figsize=(15, 10))
    for ax, metric in zip(axes, PRIMARY_METRICS):
        ranked = sorted(
            [r for r in ranking if r[f"{metric}_snr"] is not None],
            key=lambda r: (r[f"{metric}_snr"] if math.isfinite(r[f"{metric}_snr"])
                           else 1e9),
        )
        labels = [r["factor"] for r in ranked]
        snr = [min(r[f"{metric}_snr"], 1e3) if math.isfinite(r[f"{metric}_snr"])
               else 1e3 for r in ranked]
        y = range(len(labels))
        ax.barh(list(y), snr, color="tab:blue")
        for k in (1, 2, 3):
            ax.axvline(k, color="black", ls="--", alpha=0.4, lw=0.8)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xscale("symlog", linthresh=1.0)
        ax.set_xlabel("effect range / baseline seed SD  (signal-to-noise)")
        ax.set_title(metric)
        ax.grid(alpha=0.25, axis="x")
    fig.suptitle(
        "Parameter sensitivity: effect size relative to seed-only noise\n"
        "(dashed lines mark 1/2/3x the baseline seed standard deviation; "
        "no verdict applied)", fontsize=13)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "sensitivity_tornado.png", dpi=150)
    plt.close(fig)

    # 2. Response curves for the numeric factors that sweep >=3 levels.
    numeric_factors = sorted({
        e["factor"] for e in summary
        if e["factor"] != BASELINE_FACTOR and e["level_value"] is not None
    })
    numeric_factors = [
        f for f in numeric_factors
        if sum(1 for e in summary if e["factor"] == f) >= 2
    ]
    n = len(numeric_factors)
    cols = 4
    rows_n = math.ceil(n / cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(4 * cols, 3 * rows_n))
    axes = axes.flat if n > 1 else [axes]
    metric = "episodes_per_million_miles"
    base_mean = baseline[f"{metric}_mean"]
    base_sd = baseline[f"{metric}_sd"] or 0.0
    for ax, factor in zip(axes, numeric_factors):
        pts = sorted(
            [(e["level_value"], e[f"{metric}_mean"], e[f"{metric}_sd"] or 0.0)
             for e in summary if e["factor"] == factor
             and e[f"{metric}_mean"] is not None],
            key=lambda p: p[0],
        )
        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            es = [p[2] for p in pts]
            ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3)
        if base_mean is not None:
            ax.axhspan(base_mean - 2 * base_sd, base_mean + 2 * base_sd,
                       color="tab:gray", alpha=0.2)
            ax.axhline(base_mean, color="tab:gray", ls="--", lw=0.8)
        ax.set_title(factor, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25)
    for ax in list(axes)[n:]:
        ax.axis("off")
    fig.suptitle(
        "Response of episodes/million-miles to each numeric factor\n"
        "(shaded band = baseline mean +/- 2 seed SD)", fontsize=13)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "response_curves.png", dpi=150)
    plt.close(fig)


def fmt(value, spec=".4g"):
    if value is None:
        return "n/a"
    if isinstance(value, float) and not math.isfinite(value):
        return "inf"
    return format(value, spec)


def write_report(summary, ranking, baseline, meta):
    lines = [
        "# Parameter-sensitivity study (one-at-a-time)",
        "",
        "## What this answers",
        "",
        "Each simulator parameter was varied on its own from the delivered "
        "`config.yaml` baseline while every other setting was held fixed. Every "
        "variant, including the untouched baseline, was run for "
        f"{meta['replicates']} independent seed sets at "
        f"{meta['miles']:,.0f} miles each. The baseline's spread across those "
        "seeds is the **seed-only noise band** (the negative control): the "
        "natural run-to-run variation of the model when nothing is changed.",
        "",
        "A parameter's influence is reported as a **signal-to-noise ratio** = "
        "(range of a metric across the parameter's swept levels) / (baseline "
        "seed standard deviation of that metric). A ratio near or below 1 means "
        "sweeping the parameter moved the output no more than reshuffling the "
        "random seeds would---i.e. no detectable effect. A large ratio means a "
        "real effect. **No fixed cut-off is applied here**; the ranking is laid "
        "out so a threshold can be chosen from the numbers below.",
        "",
        "## Seed-only noise band (baseline, negative control)",
        "",
        "| metric | baseline mean | seed SD | seed CV |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRIC_KEYS:
        m = baseline[f"{metric}_mean"]
        sd = baseline[f"{metric}_sd"]
        cv = (sd / m) if (m not in (None, 0) and sd is not None) else None
        lines.append(f"| {metric} | {fmt(m)} | {fmt(sd)} | "
                     f"{fmt(cv, '.2%') if cv is not None else 'n/a'} |")

    lines += [
        "",
        "## Sensitivity ranking",
        "",
        "Factors sorted by their maximum signal-to-noise across the two primary "
        "outputs (episode rate and unknown-time fraction). `SNR` columns are "
        "effect-range / baseline-seed-SD; `%` columns are effect-range as a "
        "percent of the baseline mean; `trend` is the direction versus the "
        "swept level (numeric factors only).",
        "",
        "| factor | rate SNR | rate % | rate trend | unknown-frac SNR | "
        "unknown-frac % | unknown-frac trend | infeasible levels? |",
        "|---|---:|---:|---|---:|---:|---|:--:|",
    ]
    for rec in ranking:
        r_snr = rec["episodes_per_million_miles_snr"]
        u_snr = rec["unknown_time_fraction_snr"]
        lines.append(
            f"| {rec['factor']} "
            f"| {fmt(r_snr, '.1f')} "
            f"| {fmt(rec['episodes_per_million_miles_effect_pct'], '.1f')}% "
            f"| {rec['episodes_per_million_miles_trend']} "
            f"| {fmt(u_snr, '.1f')} "
            f"| {fmt(rec['unknown_time_fraction_effect_pct'], '.1f')}% "
            f"| {rec['unknown_time_fraction_trend']} "
            f"| {'yes' if rec['any_infeasible'] else ''} |"
        )

    lines += [
        "",
        "## How to read the ranking",
        "",
        "- **High SNR, clear trend** -> the parameter drives that output; the "
        "trend column says which direction.",
        "- **SNR at or below ~1** -> the sweep stayed inside the seed-noise "
        "band; no effect distinguishable from randomness at this mileage and "
        "replicate count.",
        "- Categorical factors (rarity/base-weight shapes, toggles, conditional "
        "mode) report SNR and percent effect but no numeric trend.",
        "- `transition_mode_conditional` is a **structural** variant: turning on "
        "conditional mode also requires disabling full-scenario unknowns. "
        "Compare it against the standalone `full_scenario_enabled=off` row to "
        "isolate the conditional coupling's own contribution.",
        "",
        "## Per-factor detail",
        "",
    ]
    # Per-factor tables for the primary metric.
    order = [r["factor"] for r in ranking]
    for factor in order:
        entries = sorted(
            [e for e in summary if e["factor"] == factor],
            key=lambda e: (e["level_value"] is None, e["level_value"], e["level"]),
        )
        base = baseline
        lines += [
            f"### {factor}",
            "",
            "| level | feasible | episodes/Mmi | unknown-frac | "
            "episode dur (s) | dispersion | element/hidden/full episodes |",
            "|---|:--:|---:|---:|---:|---:|---|",
            f"| {BASELINE_LABEL} | {base['feasible_runs']}/{base['replicates']} "
            f"| {fmt(base['episodes_per_million_miles_mean'], '.0f')} "
            f"| {fmt(base['unknown_time_fraction_mean'], '.3%')} "
            f"| {fmt(base['duration_s_mean_mean'], '.1f')} "
            f"| {fmt(base['dispersion_index_mean'], '.2f')} "
            f"| {fmt(base['episodes_element_mean'], '.0f')}/"
            f"{fmt(base['episodes_hidden_triggering_mean'], '.0f')}/"
            f"{fmt(base['episodes_full_scenario_mean'], '.0f')} |",
        ]
        for e in entries:
            note = "" if e["errors"] == 0 else f" ({e['errors']} infeasible)"
            lines.append(
                f"| {e['level']}{note} "
                f"| {e['feasible_runs']}/{e['replicates']} "
                f"| {fmt(e['episodes_per_million_miles_mean'], '.0f')} "
                f"| {fmt(e['unknown_time_fraction_mean'], '.3%')} "
                f"| {fmt(e['duration_s_mean_mean'], '.1f')} "
                f"| {fmt(e['dispersion_index_mean'], '.2f')} "
                f"| {fmt(e['episodes_element_mean'], '.0f')}/"
                f"{fmt(e['episodes_hidden_triggering_mean'], '.0f')}/"
                f"{fmt(e['episodes_full_scenario_mean'], '.0f')} |"
            )
        infeasible = [e for e in entries if e["error_example"]]
        if infeasible:
            lines.append("")
            for e in infeasible:
                lines.append(f"- `{e['level']}` infeasible: {e['error_example']}")
        lines.append("")

    lines += [
        "## Method",
        "",
        f"- {meta['n_variants']} variants (one baseline + "
        f"{meta['n_variants'] - 1} single-factor changes), each run for "
        f"{meta['replicates']} independent seed sets at "
        f"{meta['miles']:,.0f} miles: {meta['n_tasks']} full histories.",
        "- A replicate offsets all seven simulator seeds and the full-scenario "
        "calibration seed by the same per-replicate amount, so replicates are "
        "independent whole-model histories.",
        "- Per-layer durations were swept multiplicatively around each layer's "
        "own baseline (mean x0.5/x2, variance x0.25/x4). Element counts were "
        "pinned (min==max) at values in/around the researched ranges.",
        "- Infeasible configurations (e.g. an unknown weight that would exceed "
        "the very-rare weight) are caught per run and reported, never silently "
        "dropped.",
        "- Signal-to-noise = effect range across a factor's levels divided by "
        "the baseline seed standard deviation. No significance threshold is "
        "imposed; choose one from the tables and the noise band.",
        f"- Total wall time: {meta['wall_minutes']:.1f} minutes on "
        f"{meta['workers']} worker processes.",
        "",
        "## Files",
        "",
        "- `run_rows.csv` - every individual run (all metrics, feasibility).",
        "- `factor_summary.csv` - per factor x level aggregates (mean/sd/min/max).",
        "- `sensitivity_ranking.csv` - effect range, percent, SNR and trend per factor.",
        "- `summary.json` - full manifest and aggregates.",
        "- `sensitivity_tornado.png` - SNR ranking for the two primary metrics.",
        "- `response_curves.png` - metric response to each numeric factor.",
        "- `runs/<factor>/<level>/replicate_*/stats.json` - full per-run output.",
        "",
    ]
    (RESULTS_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8")


# ==========================================================================
# Driver
# ==========================================================================
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--miles", type=float, default=None,
                        help="miles per run (default: config target)")
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--workers", type=int, default=None,
                        help="worker processes (default: min(cpu-4, 12))")
    parser.add_argument("--factors", nargs="*", default=None,
                        help="restrict to these factor names")
    parser.add_argument("--dry-run", action="store_true",
                        help="list variants and task count, run nothing")
    args = parser.parse_args()

    cfg = SimConfig.from_yaml(str(CONFIG_PATH))
    miles = args.miles if args.miles is not None else cfg.target_total_miles
    variants = build_variants(cfg)
    if args.factors:
        wanted = set(args.factors)
        variants = [v for v in variants if v[0] in wanted]
        if not variants:
            parser.error(f"no variants match factors {sorted(wanted)}")

    # Baseline is the shared reference level of every factor: run it once.
    tasks = []
    for replicate in range(args.replicates):
        tasks.append({"factor": BASELINE_FACTOR, "level": BASELINE_LABEL,
                      "level_value": None, "spec": {"kind": "baseline"},
                      "replicate": replicate, "miles": miles})
    for factor, level, value, spec in variants:
        for replicate in range(args.replicates):
            tasks.append({"factor": factor, "level": level, "level_value": value,
                          "spec": spec, "replicate": replicate, "miles": miles})

    n_variants = len(variants) + 1
    factor_names = sorted({v[0] for v in variants})
    print(f"{n_variants} variants ({len(factor_names)} factors + baseline), "
          f"{args.replicates} replicates -> {len(tasks)} runs at "
          f"{miles:,.0f} miles each")
    if args.dry_run:
        for name in factor_names:
            levels = [v[1] for v in variants if v[0] == name]
            print(f"  {name}: {levels}")
        return

    import os
    default_workers = min(max(os.cpu_count() - 4, 1), 12)
    workers = args.workers or default_workers

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_task, task) for task in tasks]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            done += 1
            flag = "" if row["feasible"] else " INFEASIBLE"
            rate = row["episodes_per_million_miles"]
            print(f"[{done:>4}/{len(tasks)}] {row['factor']}/{row['level']} "
                  f"rep{row['replicate'] + 1} "
                  f"rate={fmt(rate, '.0f') if rate else 'n/a'}{flag}",
                  flush=True)
    wall = time.monotonic() - started

    rows.sort(key=lambda r: (r["factor"], r["level"], r["replicate"]))
    summary = aggregate(rows)
    ranking, baseline = rank_sensitivity(summary)

    meta = {
        "study": "one-at-a-time parameter sensitivity",
        "source_config": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "miles": miles,
        "replicates": args.replicates,
        "n_variants": n_variants,
        "n_tasks": len(tasks),
        "workers": workers,
        "wall_minutes": wall / 60.0,
        "seed_step": SEED_STEP,
    }

    write_csv(RESULTS_DIR / "run_rows.csv", rows)
    write_csv(RESULTS_DIR / "factor_summary.csv", summary)
    write_csv(RESULTS_DIR / "sensitivity_ranking.csv", ranking)
    with (RESULTS_DIR / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump({"meta": meta, "baseline": baseline, "ranking": ranking,
                   "factor_summary": summary}, handle, indent=2)
    make_plots(summary, ranking, baseline)
    write_report(summary, ranking, baseline, meta)

    infeasible = sum(1 for r in rows if not r["feasible"])
    print(f"\ncompleted {len(tasks)} runs ({infeasible} infeasible) in "
          f"{wall / 60:.1f} min; results in {RESULTS_DIR}")


if __name__ == "__main__":
    main()
