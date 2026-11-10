#!/usr/bin/env python3
"""Plot the GateANN rare-label exploration results."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
FONT = font_manager.FontProperties(fname=str(FONT_PATH))
plt.rcParams.update(
    {
        "font.family": FONT.get_name(),
        "font.size": 9,
        "axes.titlesize": 9.8,
        "axes.labelsize": 9,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8,
        "axes.unicode_minus": False,
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.5,
        "grid.alpha": 0.35,
        "figure.dpi": 150,
        "savefig.dpi": 300,
    }
)

S = pd.read_csv(ROOT / "exploration" / "results" / "exploration_summary.csv")
SUPP = pd.read_csv(ROOT / "results" / "supp_low_L_sweep.csv")


def row(variant, bucket, L):
    hit = S[(S.variant == variant) & (S.bucket == bucket) & (S.L == L)]
    assert len(hit) == 1, (variant, bucket, L, len(hit))
    return hit.iloc[0]


base = {
    320: row("baseline", "low", 320),
    640: row("baseline", "low", 640),
}
supp_base = SUPP[(SUPP.system == "gateann") & (SUPP.L.isin([1280, 2560]))]
seed40_graph = row("seed40+graph", "low", 320)
bfs = row("bfs2", "low", 320)
seeds = {k: row(f"seed{k}", "low", 320) for k in (20, 40, 60, 80)}
seed40_l640 = row("seed40", "low", 640)

fig, axes = plt.subplots(1, 2, figsize=(7.3, 3.45), gridspec_kw={"width_ratios": [1.15, 1.0]})
ax = axes[0]

# Baseline curve: controlled L=320/640, plus the separate 3-run L sweep for
# L=1280/2560. The latter is explicitly labeled as supplementary in the report.
bx = [base[320].mean_latency_us_median, base[640].mean_latency_us_median]
by = [base[320].recall_percent_median, base[640].recall_percent_median]
ax.plot(bx, by, color="#6B7280", marker="o", markersize=5.5, linewidth=1.3, label="GateANN baseline", zorder=2)
for L, b in base.items():
    ax.errorbar(
        b.mean_latency_us_median,
        b.recall_percent_median,
        xerr=[[b.mean_latency_us_median - b.mean_latency_us_min], [b.mean_latency_us_max - b.mean_latency_us_median]],
        yerr=[[b.recall_percent_median - b.recall_percent_min], [b.recall_percent_max - b.recall_percent_median]],
        color="#6B7280", capsize=2, elinewidth=0.8, zorder=2,
    )
for L, b in base.items():
    if L == 320:
        continue
    ax.annotate(f"L={L}", (b.mean_latency_us_median, b.recall_percent_median),
                xytext=(7, 4), textcoords="offset points", color="#4B5563", fontsize=7.8)
for _, b in supp_base.iterrows():
    ax.errorbar(
        b.mean_latency_us_median * 1.0,
        b.recall_percent_median,
        xerr=[[b.mean_latency_us_median - b.mean_latency_us_min], [b.mean_latency_us_max - b.mean_latency_us_median]],
        yerr=[[b.recall_percent_median - b.recall_percent_min], [b.recall_percent_max - b.recall_percent_median]],
        fmt="o", mfc="white", mec="#6B7280", color="#6B7280", capsize=2, elinewidth=0.8, zorder=2,
    )
    ax.annotate(f"L={int(b.L)}", (b.mean_latency_us_median, b.recall_percent_median),
                xytext=(7, -13), textcoords="offset points", color="#4B5563", fontsize=7.8)

sx = [seeds[k].mean_latency_us_median for k in (20, 40, 60, 80)]
sy = [seeds[k].recall_percent_median for k in (20, 40, 60, 80)]
ax.plot(sx, sy, color="#1f5fa8", marker="s", markersize=5.5, linewidth=1.5, label="rare-label seed-only (20–80)", zorder=4)
for k in (20, 40, 60, 80):
    b = seeds[k]
    ax.errorbar(
        b.mean_latency_us_median,
        b.recall_percent_median,
        xerr=[[b.mean_latency_us_median - b.mean_latency_us_min], [b.mean_latency_us_max - b.mean_latency_us_median]],
        yerr=[[b.recall_percent_median - b.recall_percent_min], [b.recall_percent_max - b.recall_percent_median]],
        color="#1f5fa8", capsize=2, elinewidth=0.8, zorder=4,
    )

ax.scatter(
    seed40_graph.mean_latency_us_median,
    seed40_graph.recall_percent_median,
    marker="D", s=38, color="#c44e2b", label="seeds + graph expansion", zorder=5,
)
ax.scatter(
    bfs.mean_latency_us_median,
    bfs.recall_percent_median,
    marker="*", s=95, color="#7b2d8b", label="valid-frontier BFS (H=2)", zorder=5,
)
ax.annotate("BFS H=2", (bfs.mean_latency_us_median, bfs.recall_percent_median),
            xytext=(-38, 4), textcoords="offset points", color="#7b2d8b", fontsize=7.8)
ax.scatter(
    seed40_l640.mean_latency_us_median,
    seed40_l640.recall_percent_median,
    marker="^", s=30, color="#1f5fa8", zorder=5,
)

ax.set_xscale("log")
ax.set_xlim(330, 6500)
ax.set_xticks([400, 600, 1000, 2000, 5000])
ax.set_xticklabels(["400", "600", "1000", "2000", "5000"])
ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_ylim(30, 102)
ax.set_xlabel("平均查询时延（μs，对数轴）")
ax.set_ylabel("Recall@10（%）")
ax.set_title("(a) Low workload：候选来源与 Recall–Latency", pad=6)
ax.grid(True, which="both")
ax.legend(loc="lower right", frameon=True, fontsize=7.2)

# (b) seed-limit curve
ax2 = axes[1]
limits = [20, 40, 60, 80]
rec = np.array([seeds[k].recall_percent_median for k in limits])
rlo = np.array([seeds[k].recall_percent_min for k in limits])
rhi = np.array([seeds[k].recall_percent_max for k in limits])
lat = np.array([seeds[k].mean_latency_us_median for k in limits])
llo = np.array([seeds[k].mean_latency_us_min for k in limits])
lhi = np.array([seeds[k].mean_latency_us_max for k in limits])
ax2.errorbar(limits, rec, yerr=[rec - rlo, rhi - rec], color="#1f5fa8", marker="s", markersize=5,
             linewidth=1.5, capsize=2, label="Recall@10（左轴）")
ax2.set_xlabel("种子候选数上限 $L_{seed}$")
ax2.set_ylabel("Recall@10（%）", color="#1f5fa8")
ax2.tick_params(axis="y", labelcolor="#1f5fa8")
ax2.set_ylim(88, 100.5)
ax2.set_xticks(limits)
ax2.grid(True, alpha=0.3)
ax2b = ax2.twinx()
ax2b.errorbar(limits, lat, yerr=[lat - llo, lhi - lat], color="#c44e2b", marker="o", markersize=5,
              linewidth=1.4, capsize=2, label="Mean latency（右轴）")
ax2b.set_ylabel("平均查询时延（μs）", color="#c44e2b")
ax2b.tick_params(axis="y", labelcolor="#c44e2b")
ax2b.set_ylim(330, 820)
ax2.set_title("(b) 种子上限的收益拐点", pad=6)
h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax2b.get_legend_handles_labels()
ax2.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=7.2, frameon=True)

fig.tight_layout(w_pad=2.2)
fig.savefig(FIG / "fig4_exploration_low.png", bbox_inches="tight")
fig.savefig(FIG / "fig4_exploration_low.pdf", bbox_inches="tight")
plt.close(fig)
print("wrote", FIG / "fig4_exploration_low.png")
