#!/usr/bin/env python3
"""Study: choosing concentration_scale for the Dirichlet transition vectors.

Analytical part: with alpha = c * normalized_weights, the realized unknown
probability mass of a layer follows Beta(c*p, c*(1-p)) with p the designed
unknown mass (0.004). Its standard deviation is sqrt(p*(1-p)/(c+1)), so the
relative scatter (CV) shrinks like 1/sqrt(c).

Experimental part: Monte Carlo over many Dirichlet draws for representative
layer sizes; measures the fraction of draws whose realized unknown mass lands
within +/-25% of the 0.4% target.

Outputs: concentration_study.md and concentration_study.png (same folder).
"""

import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P_TARGET = 0.004
TOL = 0.25                      # +/-25% acceptance band around the target
CANDIDATES = [100, 300, 1000, 3000, 10000, 20000, 30000, 100000]
N_DRAWS = 4000                  # Dirichlet draws per (c, layer)
CRITERION = 0.95                # required fraction inside the band
BASE_WEIGHTS = {"common": 1.0, "medium": 0.4, "rare": 0.1, "very_rare": 0.03}
PROPS = {"common": 0.50, "medium": 0.25, "rare": 0.10, "very_rare": 0.05,
         "unknown": 0.10}
RARITIES = ("common", "medium", "rare", "very_rare", "unknown")


def largest_remainder(n):
    exact = {r: n * PROPS[r] for r in RARITIES}
    counts = {r: math.floor(exact[r]) for r in RARITIES}
    rem = n - sum(counts.values())
    for r in sorted(RARITIES, key=lambda r: -(exact[r] - counts[r]))[:rem]:
        counts[r] += 1
    return counts


def layer_weights(n):
    """Normalized designed weight vector + unknown mask for a layer of n
    elements (calculated unknown-weight mode, target P_TARGET)."""
    counts = largest_remainder(n)
    known_mass = sum(counts[r] * BASE_WEIGHTS[r]
                     for r in RARITIES if r != "unknown")
    n_u = counts["unknown"]
    if n_u == 0:
        raise ValueError(f"n={n} yields no unknown elements")
    w_u = P_TARGET * known_mass / (n_u * (1 - P_TARGET))
    w = []
    mask = []
    for r in RARITIES:
        wr = BASE_WEIGHTS.get(r, w_u)
        for _ in range(counts[r]):
            w.append(wr)
            mask.append(r == "unknown")
    w = np.array(w)
    return w / w.sum(), np.array(mask)


def main():
    rng = np.random.default_rng(20260707)
    # representative unknown-bearing layers under the new element ranges
    layers = {"ego/ru-like (n=10)": 10,
              "temporal-like (n=38)": 38,
              "trigger-like (n=75)": 75}

    results = {}   # c -> {layer: (frac_in_band, p5, p95, std)}
    for c in CANDIDATES:
        results[c] = {}
        for label, n in layers.items():
            probs, mask = layer_weights(n)
            draws = rng.dirichlet(c * probs, size=N_DRAWS)
            mass = draws[:, mask].sum(axis=1)
            in_band = np.mean(np.abs(mass - P_TARGET) <= TOL * P_TARGET)
            results[c][label] = (in_band, np.percentile(mass, 5),
                                 np.percentile(mass, 95), mass.std())

    recommended = None
    for c in CANDIDATES:
        if min(v[0] for v in results[c].values()) >= CRITERION:
            recommended = c
            break

    # ---------------- report ----------------
    lines = []
    lines.append("# Concentration-Scale Study (Dirichlet transition vectors)\n")
    lines.append("Question: what `concentration_scale` (c) should be used in "
                 "`alpha = c * normalized_weights`?\n")
    lines.append("## Analytical result\n")
    lines.append("A layer's realized unknown probability mass is "
                 "Beta(c*p, c*(1-p)) with p = 0.004 (designed mass, exact by "
                 "construction of the calculated unknown weight). Its standard "
                 "deviation is sqrt(p(1-p)/(c+1)):\n")
    lines.append("| c | std of realized mass | CV (std/p) |")
    lines.append("|---|---|---|")
    for c in CANDIDATES:
        std = math.sqrt(P_TARGET * (1 - P_TARGET) / (c + 1))
        lines.append(f"| {c:,} | {std:.2e} | {std / P_TARGET:.2f} |")
    lines.append("")
    lines.append("At the old default c = 100 the CV is ~1.6: the scatter is "
                 "larger than the target itself, which is exactly why "
                 "individual layers in earlier runs landed anywhere between "
                 "~0.003% and ~0.5%. The variance is a property of the single "
                 "Dirichlet draw made at initialization, not of simulation "
                 "length.\n")
    lines.append("## Monte Carlo sweep\n")
    lines.append(f"{N_DRAWS} Dirichlet draws per value of c, for three "
                 "representative unknown-bearing layer sizes under the new "
                 "element-count ranges. Shown: fraction of draws whose "
                 "realized unknown mass lies within +/-25% of the 0.4% "
                 "target, and the 5th-95th percentile of realized mass.\n")
    header = "| c |" + "".join(f" {l} in-band | {l} p5-p95 |" for l in layers)
    lines.append(header)
    lines.append("|---|" + "---|" * (2 * len(layers)))
    for c in CANDIDATES:
        row = f"| {c:,} |"
        for label in layers:
            f_in, p5, p95, _ = results[c][label]
            row += f" {f_in:.1%} | {p5:.4%}-{p95:.4%} |"
        lines.append(row)
    lines.append("")
    lines.append("## Recommendation\n")
    if recommended is None:
        lines.append("No candidate met the criterion; increase c further.")
    else:
        lines.append(
            f"Criterion: smallest c for which **>= {CRITERION:.0%} of draws "
            f"land within +/-25% of the 0.4% target in every representative "
            f"layer**. Result: **c = {recommended:,}** (set as the new "
            "default `concentration_scale` in config.yaml).\n")
    lines.append("Trade-off: higher c keeps the sampled vectors close to the "
                 "designed rarity weights (faithful unknown rates); lower c "
                 "gives more random transition behavior at the cost of large "
                 "per-layer deviations from the 0.4% design target. If more "
                 "transition randomness is wanted, lower c consciously and "
                 "accept the wider band shown above.\n")

    with open("concentration_study.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---------------- plot ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    for label in layers:
        fr = [results[c][label][0] for c in CANDIDATES]
        ax1.plot(CANDIDATES, fr, "o-", label=label)
    ax1.axhline(CRITERION, color="tab:red", ls="--", label=f"criterion {CRITERION:.0%}")
    if recommended:
        ax1.axvline(recommended, color="tab:green", ls=":",
                    label=f"recommended c = {recommended:,}")
    ax1.set_xscale("log")
    ax1.set_xlabel("concentration_scale c (log)")
    ax1.set_ylabel("fraction of draws within ±25% of 0.4%")
    ax1.set_title("Adherence to the unknown-rate design target")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    for label in layers:
        p5 = [results[c][label][1] for c in CANDIDATES]
        p95 = [results[c][label][2] for c in CANDIDATES]
        ax2.fill_between(CANDIDATES, p5, p95, alpha=0.25, label=f"{label} p5–p95")
    ax2.axhline(P_TARGET, color="tab:red", ls="--", label="target 0.4%")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("concentration_scale c (log)")
    ax2.set_ylabel("realized unknown mass (log)")
    ax2.set_title("Spread of realized unknown mass vs c")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("concentration_study.png", dpi=150)

    print(f"recommended concentration_scale: {recommended}")
    for c in CANDIDATES:
        print(c, {l: f"{results[c][l][0]:.3f}" for l in layers})


if __name__ == "__main__":
    main()
