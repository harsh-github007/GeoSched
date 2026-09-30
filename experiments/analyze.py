"""Tables and charts from results/<source>.json: the counterparts of the paper's Table VI and Figs 6-8.

    python experiments/analyze.py            # synthetic
    python experiments/analyze.py google
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DCS = ["Chile", "Finland", "Iowa", "Oregon", "Singapore"]
COLORS = {"Chile": "#2f9e44", "Finland": "#1c7ed6", "Iowa": "#e03131", "Oregon": "#ae3ec9", "Singapore": "#f59f00"}
MON = {1: "Jan", 3: "Mar", 5: "May", 7: "Jul", 9: "Sep", 11: "Nov"}
METRICS = [("utilization_pct", "CPU utilisation (%)", "utilization"),
           ("job_energy_kj", "Energy (GJ)", "energy"), ("job_cost_usd", "Cost ($)", "cost")]


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "synthetic"
    data = json.loads((ROOT / "results" / f"{source}.json").read_text())
    runs = {(r["month"], r["scheduler"]): r["datacenters"] for r in data["runs"]}
    months = sorted({m for m, _ in runs})

    tot = {s: {k: sum(runs[(m, s)][d][k] for m in months for d in DCS) for k in ("job_energy_kj", "job_cost_usd")}
           for s in ("dumbsched", "geosched")}
    e0, e1 = tot["dumbsched"]["job_energy_kj"] / 1e6, tot["geosched"]["job_energy_kj"] / 1e6
    c0, c1 = tot["dumbsched"]["job_cost_usd"], tot["geosched"]["job_cost_usd"]
    per_month = []
    for m in months:
        a = sum(runs[(m, "dumbsched")][d]["job_cost_usd"] for d in DCS)
        b = sum(runs[(m, "geosched")][d]["job_cost_usd"] for d in DCS)
        ea = sum(runs[(m, "dumbsched")][d]["job_energy_kj"] for d in DCS)
        eb = sum(runs[(m, "geosched")][d]["job_energy_kj"] for d in DCS)
        per_month.append(dict(month=MON[m], cost_saving_pct=100 * (a - b) / a, energy_saving_pct=100 * (ea - eb) / ea))

    md = [f"# Results ({source} traces)", "",
          "Six 5-day simulations (the 15th of Jan, Mar, May, Jul, Sep and Nov 2013), five data centers each. "
          "Energy and cost are for running the jobs, including their cooling, as in the paper's Table VI.", "",
          "| | Energy (GJ) | Cost ($) |", "| --- | ---: | ---: |",
          f"| DumbSched | {e0:,.1f} | {c0:,.0f} |", f"| GeoSched | {e1:,.1f} | {c1:,.0f} |",
          f"| Saving | {e0 - e1:,.1f} ({100 * (e0 - e1) / e0:.1f}%) | {c0 - c1:,.0f} ({100 * (c0 - c1) / c0:.1f}%) |", "",
          "| Month | Cost saving | Energy saving |", "| --- | ---: | ---: |"]
    md += [f"| {p['month']} | {p['cost_saving_pct']:.1f}% | {p['energy_saving_pct']:.1f}% |" for p in per_month]
    md += ["", "Paper (Table VI): energy saving 8.2%, cost saving 11.7%."]
    (ROOT / "results" / f"{source}.md").write_text("\n".join(md) + "\n")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, (key, label, _) in zip(axes, METRICS):
        for d in DCS:
            scale = 1e6 if key == "job_energy_kj" else 1
            for s, ls, mk in (("geosched", "-", "o"), ("dumbsched", "--", None)):
                ax.plot([MON[m] for m in months], [runs[(m, s)][d][key] / scale for m in months], ls=ls, marker=mk,
                        ms=4, color=COLORS[d], label=f"{d}" if s == "geosched" else None, lw=1.6 if s == "geosched" else 1)
        ax.set_ylabel(label)
        ax.grid(alpha=.25)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, fontsize=8, title="solid: GeoSched\ndashed: DumbSched", title_fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "results" / f"{source}.png", dpi=150)

    summary = dict(source=source, months=[MON[m] for m in months], datacenters=DCS,
                   totals=dict(energy_gj=[e0, e1], cost_usd=[c0, c1]), per_month=per_month,
                   series={s: {d: {k: [runs[(m, s)][d][k] for m in months] for k, _, _ in METRICS} for d in DCS}
                           for s in ("dumbsched", "geosched")})
    (ROOT / "results" / f"{source}_summary.json").write_text(json.dumps(summary))
    print("\n".join(md))


if __name__ == "__main__":
    main()
