#!/usr/bin/env python3
"""Charts for the Phoenix pre-RTL verification report (reads results_v2.json)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

import os
D = os.path.dirname(os.path.abspath(__file__))
r = json.load(open(f"{D}/results_v2.json"))
INK, SEC, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#ffffff"
BLUE, AQUA, VIOLET, YELLOW, RED, ORANGE, GREY = "#2a78d6", "#1baf7a", "#6250d6", "#eda100", "#e34948", "#eb6834", "#c3c2b7"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.edgecolor": AXIS,
                     "axes.labelcolor": SEC, "xtick.color": MUTED, "ytick.color": SEC, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.dpi": 200})

GROUPS = [("Detected and recovered", ["Detected and recovered"], BLUE, "#fff"),
          ("Corrected by memory ECC", ["Corrected by memory ECC"], AQUA, "#fff"),
          ("Correct after system reset, or safe state", ["Correct after system reset", "Safe state"], VIOLET, "#fff"),
          ("No effect (overwritten or cleared)", ["No effect (overwritten or cleared)"], GREY, INK),
          ("Flagged by ECC, not correctable", ["Flagged by ECC, not correctable"], "#8f8d86", "#fff"),
          ("Hidden fault left in a core", ["Latent (hidden, not cleared)"], YELLOW, INK),
          ("Wrong result, hang or crash", ["Wrong result", "Hang", "Crash"], RED, "#fff")]
E = r["experiments"]
def pct(e, cfg, keys): return 100 * sum(e[cfg]["counts"].get(k, 0) for k in keys) / e["n"]
UN = ["Latent (hidden, not cleared)", "Wrong result", "Hang", "Crash"]
DE = ["Detected and recovered", "Corrected by memory ECC"]

def stacked(rows, fname, title, height):
    fig, ax = plt.subplots(figsize=(8.2, height))
    used = set()
    for i, (lab, e, cfg) in enumerate(rows):
        left = 0
        for name, keys, col, tc in GROUPS:
            v = pct(e, cfg, keys)
            if v <= 0: continue
            ax.barh(i, v, left=left, color=col, edgecolor=SURF, linewidth=2, height=0.62, label=name if name not in used else None)
            used.add(name)
            if v >= 6: ax.text(left + v / 2, i, f"{v:.1f}%", ha="center", va="center", color=tc, fontsize=9, fontweight="bold")
            left += v
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([x[0] for x in rows]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel("Share of fault-injection runs (%)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False); ax.tick_params(length=0)
    ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=10)
    h, l = ax.get_legend_handles_labels()
    order = [n for n, *_ in GROUPS if n in l]
    ax.legend([h[l.index(n)] for n in order], order, loc="upper center", bbox_to_anchor=(0.45, -0.32 if height < 3 else -0.16),
              ncol=2, frameon=False, fontsize=9, handlelength=1.2)
    fig.savefig(f"{D}/{fname}", bbox_inches="tight"); plt.close(fig)

# Fig 1: single core fault, three configurations
c = E["core"]
stacked([("One unprotected core", c, "single_core"), ("Three cores, before", c, "before"), ("Three cores, after", c, "after")],
        "fig1_core_outcomes.png", f"One bit flip in one core: outcome of {c['n']:,} runs per configuration", 2.6)

# Fig 2: all fault classes, before and after
rows = []
for k, short in (("core", "1 flip, one core"), ("mem1", "1 flip, memory word"), ("mem2", "2 flips, memory word"),
                 ("dbl_far", "2 cores, separate times"), ("dbl_near", "2 cores, within 3 cycles"), ("perm", "Permanent core fault")):
    rows += [(f"{short}  |  before", E[k], "before"), (f"{short}  |  after", E[k], "after")]
stacked(rows, "fig2_all_classes.png", "Outcome by fault class, before and after the three mechanisms", 6.2)

# Fig 3: unresolved share, before vs after (grouped bars)
keys = ["core", "mem1", "mem2", "dbl_far", "dbl_near"]
labs = ["1 flip,\none core", "1 flip,\nmemory word", "2 flips,\nmemory word", "2 cores,\nseparate times", "2 cores,\nwithin 3 cycles"]
def grouped(vals_b, vals_a, fname, title, ylab, ymax):
    fig, ax = plt.subplots(figsize=(8.2, 3.3)); w = 0.34
    for i, (b, a) in enumerate(zip(vals_b, vals_a)):
        ax.bar(i - w / 2 - 0.02, b, w, color=ORANGE, label="Before" if i == 0 else None)
        ax.bar(i + w / 2 + 0.02, a, w, color=BLUE, label="After" if i == 0 else None)
        ax.text(i - w / 2 - 0.02, b + ymax * 0.015, f"{b:.1f}%", ha="center", va="bottom", fontsize=9, color=INK)
        ax.text(i + w / 2 + 0.02, a + ymax * 0.015, f"{a:.1f}%", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs); ax.set_ylim(0, ymax); ax.set_ylabel(ylab)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
    ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", pad=10)
    ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=9.5)
    fig.savefig(f"{D}/{fname}", bbox_inches="tight"); plt.close(fig)
grouped([pct(E[k], "before", UN) for k in keys], [pct(E[k], "after", UN) for k in keys], "fig3_unresolved.png",
        "Unresolved runs: wrong result, hang, or hidden fault left behind", "Share of runs (%)", 85)
grouped([pct(E[k], "before", DE) for k in keys], [pct(E[k], "after", DE) for k in keys], "fig4_detected.png",
        "Runs where the fault was detected and recovered, or corrected", "Share of runs (%)", 110)

# Fig 5: scrub period sweep, two panels (one measure each; never a dual axis)
sw = [s for s in r["scrub_sweep"]]
sw = sorted(sw, key=lambda s: (s["period"] == 0, -s["period"]))          # 800 ... 50, then off
sw = [s for s in sw if s["period"] == 0] + [s for s in sw if s["period"]]
xl = ["off" if s["period"] == 0 else str(s["period"]) for s in sw]
lat = [100 * s["counts"].get("Latent (hidden, not cleared)", 0) / s["n"] for s in sw]
ov = [100 * s["overhead"] for s in sw]
fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.0))
for ax, y, col, ttl in ((axs[0], lat, YELLOW, "Hidden faults left in a core (%)"), (axs[1], ov, BLUE, "Extra run time, fault-free (%)")):
    ax.bar(range(len(xl)), y, 0.6, color=col)
    for i, v in enumerate(y): ax.text(i, v + max(y) * 0.02, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(xl))); ax.set_xticklabels(xl); ax.set_xlabel("Scrub period (cycles)")
    ax.set_ylim(0, max(y) * 1.15); ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
    ax.set_title(ttl, loc="left", fontsize=10.5, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{D}/fig5_scrub_sweep.png", bbox_inches="tight"); plt.close(fig)

# Fig 6: detection latency distribution, before vs after
ed = c["before"]["latency_edges"]; hb, ha = c["before"]["latency_hist"], c["after"]["latency_hist"]
nb, na = sum(hb), sum(ha)
bl = [f"{ed[i]}–{ed[i+1]-1}" for i in range(len(ed) - 1)] + [f"{ed[-1]}+"]
fig, ax = plt.subplots(figsize=(8.2, 3.0)); w = 0.36
ax.bar([i - w / 2 - 0.02 for i in range(len(bl))], [100 * v / nb for v in hb], w, color=ORANGE, label="Before")
ax.bar([i + w / 2 + 0.02 for i in range(len(bl))], [100 * v / na for v in ha], w, color=BLUE, label="After (scrub every 400 cycles)")
ax.set_xticks(range(len(bl))); ax.set_xticklabels(bl, fontsize=9); ax.set_xlabel("Cycles from bit flip to detection")
ax.set_ylabel("Share of detected faults (%)"); ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
ax.set_title("Detection latency: the long tail disappears with periodic resynchronisation", loc="left", fontsize=11.5, fontweight="bold", pad=10)
ax.legend(frameon=False, fontsize=9.5)
fig.savefig(f"{D}/fig6_latency.png", bbox_inches="tight"); plt.close(fig)
print("charts written")
