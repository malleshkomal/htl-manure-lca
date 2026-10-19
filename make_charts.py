"""Draw the thesis results as PNG charts in results/charts/.

Usage: python make_charts.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from htlmodel import lca  # noqa: E402
from htlmodel.mass_balance import htl_balance, treatment_balance  # noqa: E402

DATA = ROOT / "data" / "thesis_tables"
OUT = ROOT / "results" / "charts"

SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
MUTED = "#b9b8b1"
SOURCE = "Source: K. M. Chougule, MSc thesis, TU Bergakademie Freiberg (2022). Aspen Plus + GaBi 9.1, CML 2001."

CONTRIB_COLOR = {
    "HTL conversion": BLUE, "Electricity": ORANGE, "Truck (EURO 5)": AQUA, "Diesel mix at refinery": YELLOW,
    "Hydrothermal gasification": VIOLET, "Fractional distillation": MAGENTA, "Desalinated water": MUTED, "Heat": "#8b8a84",
}
SCEN_ORDER = [(c, e) for c in ("case1", "case2", "case3") for e in ("wind", "grid")]
SCEN_LABEL = {("case1", "wind"): "Case 1\nwind", ("case1", "grid"): "Case 1\ngrid",
              ("case2", "wind"): "Case 2 (HTG)\nwind", ("case2", "grid"): "Case 2 (HTG)\ngrid",
              ("case3", "wind"): "Case 3 (FD)\nwind", ("case3", "grid"): "Case 3 (FD)\ngrid"}


def figure(w, h, title, subtitle=None):
    fig = plt.figure(figsize=(w, h), facecolor=SURFACE)
    fig.text(0.02, 0.97, title, fontsize=15, fontweight="bold", color=TEXT, va="top")
    if subtitle:
        fig.text(0.02, 0.905, subtitle, fontsize=10.5, color=TEXT_2, va="top")
    fig.text(0.02, 0.015, SOURCE, fontsize=8, color=TEXT_2)
    return fig


def style(ax, grid_axis="x"):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_2, length=0, labelsize=10)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / name, dpi=170, facecolor=SURFACE)
    plt.close(fig)
    print("wrote", (OUT / name).relative_to(ROOT))


def ribbon(ax, x0, y0, x1, y1, w, color, alpha=0.45):
    xm = (x0 + x1) / 2
    verts = [(x0, y0), (xm, y0), (xm, y1), (x1, y1), (x1, y1 + w), (xm, y1 + w), (xm, y0 + w), (x0, y0 + w), (x0, y0)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, alpha=alpha, lw=0))


def contributor_group(name):
    return "Electricity" if name.startswith("Electricity") else name


def chart_mass_balance():
    b = htl_balance()
    fig = figure(12.5, 6.2, "HTL mass balance: 2,000 t/day of wet cattle manure",
                 "kg/h from the Aspen Plus base case. Ribbon width is proportional to mass.")
    ax = fig.add_axes([0.02, 0.07, 0.96, 0.78])
    ax.axis("off")
    total = b.total_in
    k, gap, nw = 1.0 / total * 0.80, 0.045, 0.012
    ax.set_xlim(0, 1)
    ax.set_ylim(1.0, -0.05)
    # inputs
    ins = [("Wet manure", b.manure, BLUE), ("Make-up water", b.water, AQUA)]
    outs = [("Aqueous phase", b.aqueous, AQUA), ("Gas", b.gas, MUTED), ("Biocrude", b.biocrude, ORANGE), ("Solids (char + ash)", b.solids, YELLOW)]
    y = 0.0
    hx = 0.42
    hy = 0.0
    for name, v, c in ins:
        h = v * k
        ax.add_patch(plt.Rectangle((0.10, y), nw, h, color=TEXT))
        ribbon(ax, 0.10 + nw, y, hx, hy, h, c)
        ax.text(0.095, y + h / 2, f"{name}\n{v:,.0f} kg/h", ha="right", va="center", fontsize=10, color=TEXT)
        y += h + gap
        hy += h
    ax.add_patch(plt.Rectangle((hx, 0), nw * 1.4, total * k, color=TEXT))
    ax.text(hx + 0.01, -0.03, f"HTL reactor  ·  20 wt% solids slurry  ·  {total:,.0f} kg/h", ha="center", fontsize=10, color=TEXT, fontweight="bold")
    y, hy = 0.0, 0.0
    for name, v, c in outs:
        h = v * k
        ribbon(ax, hx + nw * 1.4, hy, 0.68, y, h, c)
        ax.add_patch(plt.Rectangle((0.68, y), nw, h, color=TEXT))
        ax.text(0.70, y + h / 2, f"{name}: {v:,.0f} kg/h ({100 * v / total:.1f}%)", va="center", fontsize=10, color=TEXT)
        y += h + gap
        hy += h
    save(fig, "01_mass_balance.png")


def chart_yields():
    b = htl_balance()
    y = b.yields_dry()
    per = b.per_kg_biocrude()
    fig = figure(12, 4.6, "Product yields from the dry manure",
                 f"Dry feed {b.dry_solids:,.0f} kg/h (21.2% of wet manure). Yields include water that reacts, so they sum to just over 100%.")
    ax = fig.add_axes([0.13, 0.15, 0.36, 0.62])
    style(ax)
    names = ["Biocrude", "Solids (char + ash)", "Gas"]
    vals = [y["biocrude"], y["solids"], y["gas"]]
    bars = ax.barh(names[::-1], vals[::-1], color=[MUTED, YELLOW, ORANGE], height=0.6)
    for bar, v in zip(bars, vals[::-1]):
        ax.text(v + 1, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontsize=10.5, color=TEXT)
    ax.set_xlim(0, 60)
    ax.set_title("Yield, % of dry feed", loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
    ax2 = fig.add_axes([0.63, 0.15, 0.33, 0.62])
    style(ax2)
    keys = [("manure", "Wet manure in"), ("aqueous", "Aqueous phase"), ("gas", "Gas"), ("water", "Water added"), ("solids", "Solids")]
    vals2 = [per[k] for k, _ in keys]
    bars = ax2.barh([n for _, n in keys][::-1], vals2[::-1], color=BLUE, height=0.6)
    for bar, v in zip(bars, vals2[::-1]):
        ax2.text(v + 0.3, bar.get_y() + bar.get_height() / 2, f"{v:.2f} kg", va="center", fontsize=10.5, color=TEXT)
    ax2.set_xlim(0, 21)
    ax2.set_title("Per 1 kg of biocrude", loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
    save(fig, "02_yields.png")


def chart_offgas():
    d = pd.read_csv(DATA / "offgas_composition.csv").sort_values("wt_percent")
    fig = figure(9, 4.2, "Off-gas is two-thirds CO₂", "Composition of the HTL gas phase, wt% (Aspen Plus)")
    ax = fig.add_axes([0.1, 0.14, 0.82, 0.62])
    style(ax)
    colors = [BLUE if c == "CO2" else MUTED for c in d["component"]]
    labels = [c.replace("2", "₂").replace("4", "₄") for c in d["component"]]
    bars = ax.barh(labels, d["wt_percent"], color=colors, height=0.6)
    for bar, v in zip(bars, d["wt_percent"]):
        ax.text(v + 0.8, bar.get_y() + bar.get_height() / 2, f"{v}%", va="center", fontsize=10.5, color=TEXT)
    ax.set_xlim(0, 80)
    save(fig, "03_offgas_composition.png")


def chart_feedstock():
    d = pd.read_csv(DATA / "manure_composition.csv").set_index("property")
    fig = figure(12.5, 4.8, "Cattle manure compared with other manures", "Elemental (daf) and proximate (dry) analysis, wt%")
    series = [("cattle_manure_this_study", "Cattle manure (this study)", BLUE),
              ("dairy_manure_ref104", "Dairy manure [104]", ORANGE), ("swine_manure_ref105", "Swine manure [105]", AQUA)]
    for i, (props, title) in enumerate([(["C", "H", "O", "N", "S"], "Elemental composition"),
                                        (["volatile_matter", "fixed_carbon", "ash"], "Proximate analysis")]):
        ax = fig.add_axes([0.07 + i * 0.5, 0.15, 0.4, 0.6])
        style(ax, "y")
        x = np.arange(len(props))
        for j, (col, name, c) in enumerate(series):
            vals = pd.to_numeric(d.loc[props, col], errors="coerce").values
            ax.bar(x + (j - 1) * 0.26, np.nan_to_num(vals), width=0.24, color=c, label=name, edgecolor=SURFACE, linewidth=1)
        ax.set_xticks(x, [p.replace("_", " ").capitalize() if len(p) > 1 else p for p in props])
        ax.set_title(title, loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
        ax.set_ylabel("wt%", color=TEXT_2)
    fig.legend(*fig.axes[0].get_legend_handles_labels(), loc="upper right", frameon=False, fontsize=9.5, ncol=3, bbox_to_anchor=(0.99, 0.965))
    save(fig, "04_feedstock_composition.png")


def chart_biocrude():
    d = pd.read_csv(DATA / "biocrude_properties.csv").set_index("property")
    fig = figure(12.5, 4.8, "HTL upgrades manure into an energy-dense biocrude",
                 "Raw manure vs HTL biocrude: more carbon and hydrogen, less nitrogen; HHV from 7.9 to 39.1 MJ/kg")
    ax = fig.add_axes([0.06, 0.15, 0.48, 0.6])
    style(ax, "y")
    el = ["C", "H", "O", "N", "S"]
    x = np.arange(len(el))
    ax.bar(x - 0.2, d.loc[el, "raw_manure_this_study"], width=0.38, color=MUTED, label="Raw manure")
    ax.bar(x + 0.2, d.loc[el, "htl_biocrude_this_study"], width=0.38, color=BLUE, label="HTL biocrude")
    ax.set_xticks(x, el)
    ax.set_ylabel("wt%", color=TEXT_2)
    ax.legend(frameon=False, fontsize=9.5)
    ax.set_title("Elemental composition, this study", loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
    ax2 = fig.add_axes([0.66, 0.15, 0.31, 0.6])
    style(ax2)
    cols = [("htl_biocrude_this_study", "This study"), ("cattle_manure_ref34", "Cattle [34]"),
            ("swine_manure_ref35", "Swine [35]"), ("dairy_manure_ref36", "Dairy [36]")]
    vals = [float(d.loc["HHV", c]) for c, _ in cols]
    bars = ax2.barh([n for _, n in cols][::-1], vals[::-1], color=[MUTED, MUTED, MUTED, BLUE], height=0.6)
    for bar, v in zip(bars, vals[::-1]):
        ax2.text(v + 0.5, bar.get_y() + bar.get_height() / 2, f"{v:.1f}", va="center", fontsize=10.5, color=TEXT)
    ax2.set_xlim(0, 46)
    ax2.set_title("Biocrude HHV, MJ/kg", loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
    save(fig, "05_biocrude_quality.png")


def stacked(ax, category, absolute=True):
    c = lca.contributions()
    c = c[c["category"] == category].copy()
    c["group"] = c["contributor"].map(contributor_group)
    piv = c.pivot_table(index=["case", "electricity"], columns="group", values="value", aggfunc="sum").fillna(0)
    piv = piv.reindex(SCEN_ORDER)
    if not absolute:
        piv = piv.div(piv.sum(axis=1), axis=0) * 100
    order = [g for g in CONTRIB_COLOR if g in piv.columns]
    left = np.zeros(len(piv))
    y = np.arange(len(piv))[::-1]
    for g in order:
        ax.barh(y, piv[g].values, left=left, color=CONTRIB_COLOR[g], height=0.62, label=g, edgecolor=SURFACE, linewidth=1.2)
        left += piv[g].values
    ax.set_yticks(y, [SCEN_LABEL[i] for i in piv.index])
    return piv, left, y


def chart_gwp():
    fig = figure(12.5, 6.0, "Climate impact: 1.26–1.78 kg CO₂ eq per kg of bio-oil",
                 "Global warming potential (GWP100) by contributor. The HTL conversion step dominates; grid electricity adds about 0.4 kg.")
    ax = fig.add_axes([0.13, 0.14, 0.62, 0.68])
    style(ax)
    piv, totals, y = stacked(ax, "GWP")
    for yi, t in zip(y, totals):
        ax.text(t + 0.02, yi, f"{t:.2f}", va="center", fontsize=10.5, color=TEXT, fontweight="bold")
    ax.set_xlim(0, 2.0)
    ax.set_xlabel("kg CO₂ eq per kg bio-oil", color=TEXT_2)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    save(fig, "06_gwp_by_contributor.png")


def chart_shares():
    fig = figure(13, 9.8, "What drives each impact category",
                 "Share of each contributor in the total, per kg of bio-oil. Transport dominates AP, EP and toxicity unless grid electricity is used.")
    for i, cat in enumerate(["GWP", "AP", "EP", "FAETP"]):
        ax = fig.add_axes([0.11 + (i % 2) * 0.46, 0.55 - (i // 2) * 0.40, 0.36, 0.29])
        style(ax)
        stacked(ax, cat, absolute=False)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
        ax.tick_params(axis="y", labelsize=8.5)
        ax.set_title(lca.CATEGORIES[cat], loc="left", fontsize=11.5, color=TEXT, fontweight="bold")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CONTRIB_COLOR.values()]
    fig.legend(handles, list(CONTRIB_COLOR), loc="lower center", ncol=4, frameon=False, fontsize=9.5, bbox_to_anchor=(0.5, 0.035))
    save(fig, "07_contribution_shares.png")


def chart_wind_vs_grid():
    t = lca.totals()
    fig = figure(13, 4.6, "Wind electricity cuts every impact category",
                 "Total impact per kg of bio-oil, wind vs German grid electricity (same for all three cases except GWP)")
    for i, cat in enumerate(["GWP", "AP", "EP", "FAETP"]):
        ax = fig.add_axes([0.05 + i * 0.245, 0.15, 0.19, 0.6])
        style(ax, "y")
        unit = lca.contributions().query("category == @cat")["unit"].iloc[0]
        x = np.arange(3)
        w = [t[(c, "wind", cat)] for c in ("case1", "case2", "case3")]
        g = [t[(c, "grid", cat)] for c in ("case1", "case2", "case3")]
        scale = 1 if cat == "GWP" else 1e3
        ax.bar(x - 0.2, np.array(w) * scale, width=0.38, color=AQUA, label="Wind")
        ax.bar(x + 0.2, np.array(g) * scale, width=0.38, color=ORANGE, label="German grid")
        ax.set_xticks(x, ["Case 1", "Case 2", "Case 3"])
        ax.set_title(f"{cat}\n{'' if scale == 1 else 'g'}{unit if scale == 1 else unit[2:]}", loc="left", fontsize=10.5, color=TEXT, fontweight="bold")

    fig.legend([plt.Rectangle((0, 0), 1, 1, color=AQUA), plt.Rectangle((0, 0), 1, 1, color=ORANGE)], ["Wind electricity", "German grid mix"],
               loc="upper right", frameon=False, fontsize=9.5, ncol=2, bbox_to_anchor=(0.99, 0.965))
    save(fig, "08_wind_vs_grid.png")


def chart_air_emissions():
    d = pd.read_csv(DATA / "air_emissions_case1_wind.csv")
    d = d[d["total"] > 1e-12].sort_values("total")
    fig = figure(11, 5.2, "Air emissions per kg of bio-oil (case 1, wind)",
                 "Fossil CO₂ from HTL conversion is about 1,000 times larger than any other emission. Log scale.")
    ax = fig.add_axes([0.25, 0.12, 0.66, 0.68])
    style(ax)
    ax.set_xscale("log")
    colors = [BLUE if "fossil" in s else MUTED for s in d["substance"]]
    bars = ax.barh(d["substance"], d["total"], color=colors, height=0.6)
    for bar, v in zip(bars, d["total"]):
        ax.text(v * 1.3, bar.get_y() + bar.get_height() / 2, f"{v:.2g} kg", va="center", fontsize=9.5, color=TEXT)
    ax.set_xlim(1e-8, 30)
    save(fig, "09_air_emissions.png")


def chart_allocation():
    d = pd.read_csv(DATA / "allocation.csv")
    fig = figure(10, 4.2, "Allocating impacts between co-products",
                 "Share of impacts given to each product: economic allocation favours biocrude (400 €/t vs 200 €/t for biochar)")
    ax = fig.add_axes([0.14, 0.15, 0.66, 0.6])
    style(ax, None)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    colors = {"biocrude": ORANGE, "biochar": YELLOW, "wastewater": AQUA}
    for i, col in enumerate(["mass_allocation_pct", "economic_allocation_pct"]):
        left = 0
        for r in d.itertuples(index=False):
            v = getattr(r, col)
            ax.barh(i, v, left=left, color=colors[r.product], height=0.55, edgecolor=SURFACE, linewidth=1.5)
            if v >= 10:
                ax.text(left + v / 2, i, f"{r.product}\n{v:g}%", ha="center", va="center", fontsize=10, color=TEXT)
            else:
                ax.text(101, i, f"{r.product} {v:g}%", va="center", fontsize=9.5, color=TEXT_2)
            left += v
    ax.set_yticks([0, 1], ["Mass", "Economic"])
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    save(fig, "10_allocation.png")


def chart_water():
    d = pd.read_csv(DATA / "water_footprint.csv")
    fig = figure(10, 4.4, "Water footprint of pre-processing", "Share of total water consumption attributed to pre-processing, %")
    ax = fig.add_axes([0.08, 0.14, 0.86, 0.62])
    style(ax, "y")
    x = np.arange(len(d))
    ax.bar(x - 0.2, d["wind_electricity_pct"], width=0.38, color=AQUA, label="Wind electricity")
    ax.bar(x + 0.2, d["grid_electricity_pct"], width=0.38, color=ORANGE, label="German grid mix")
    for xi, (a, b) in enumerate(zip(d["wind_electricity_pct"], d["grid_electricity_pct"])):
        ax.text(xi - 0.2, a + 1.5, f"{a:g}%", ha="center", fontsize=10, color=TEXT)
        ax.text(xi + 0.2, b + 1.5, f"{b:g}%", ha="center", fontsize=10, color=TEXT)
    ax.set_xticks(x, d["indicator"])
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9.5)
    save(fig, "11_water_footprint.png")


def chart_aqueous_treatment():
    aq = htl_balance().aqueous
    rows = [("Case 2: hydrothermal gasification", treatment_balance(aq, "case2")),
            ("Case 3: fractional distillation", treatment_balance(aq, "case3"))]
    fig = figure(11, 3.8, "Treating the aqueous phase recovers 99% as clean water",
                 f"{aq:,.0f} kg/h of HTL aqueous phase split into water (COD < 250 mg/L) and gas / volatile organics")
    ax = fig.add_axes([0.25, 0.16, 0.68, 0.56])
    style(ax, None)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    for i, (name, r) in enumerate(rows):
        ax.barh(i, r["water"], color=AQUA, height=0.55)
        ax.barh(i, r["gas_volatiles"] * 20, left=r["water"], color=VIOLET, height=0.55)
        ax.text(r["water"] / 2, i, f"Clean water {r['water']:,.0f} kg/h ({100 * r['water'] / aq:.1f}%)", ha="center", va="center", fontsize=10, color="white", fontweight="bold")
        ax.text(r["water"] + r["gas_volatiles"] * 20 + 400, i, f"Gas {r['gas_volatiles']:,.0f} kg/h", va="center", fontsize=10, color=TEXT)
    ax.set_yticks([0, 1], [n for n, _ in rows])
    ax.set_xlim(0, aq * 1.3)
    ax.invert_yaxis()
    fig.text(0.25, 0.085, "Gas bars drawn 20× wider so they are visible.", fontsize=8.5, color=TEXT_2)
    save(fig, "12_aqueous_treatment.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for chart in (chart_mass_balance, chart_yields, chart_offgas, chart_feedstock, chart_biocrude, chart_gwp,
                  chart_shares, chart_wind_vs_grid, chart_air_emissions, chart_allocation, chart_water, chart_aqueous_treatment):
        chart()


if __name__ == "__main__":
    main()
