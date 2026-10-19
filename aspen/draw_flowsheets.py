"""Redraw the three Aspen Plus flowsheets of the thesis (Figs 3.2, 3.3, 3.4) as PNG.

Usage: python aspen/draw_flowsheets.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).parent
SURFACE, TEXT, TEXT_2, LINE = "#fcfcfb", "#0b0b0b", "#52514e", "#8b8a84"
KIND = {  # block family -> fill colour
    "feed": "#e8e7e3", "product": "#e8e7e3",
    "pump": "#dbe8f8", "reactor": "#fde3d6", "mixer": "#dbe8f8", "separator": "#d6f1e6", "column": "#d6f1e6",
}

# name: (x, y, kind, aspen model)
COMMON = {
    "WATER": (0.5, 3.2, "feed", ""), "MANURE": (0.5, 1.6, "feed", ""),
    "P50": (2.0, 3.2, "pump", "Pump 50 bar"), "P100": (3.4, 3.2, "pump", "Pump 100 bar"),
    "DECOMPOS": (2.0, 1.6, "reactor", "RYield"), "MX1": (4.6, 2.4, "mixer", "Mixer"),
    "HYDROLYS": (6.0, 2.4, "reactor", "RYield"), "SPLIT": (7.4, 2.4, "separator", "Split"),
    "SOLID": (7.4, 0.9, "product", ""), "SECONDAR": (8.8, 2.4, "reactor", "RGibbs"),
    "F1": (10.2, 2.4, "separator", "Flash 30 °C, 1 bar"), "SYNGAS": (10.2, 3.9, "product", ""),
    "SEP": (11.6, 1.6, "separator", "Sep"), "BIOCRUDE": (11.6, 0.3, "product", ""),
}
COMMON_LINKS = [("WATER", "P50"), ("P50", "P100"), ("P100", "MX1"), ("MANURE", "DECOMPOS"), ("DECOMPOS", "MX1"),
                ("MX1", "HYDROLYS"), ("HYDROLYS", "SPLIT"), ("SPLIT", "SOLID"), ("SPLIT", "SECONDAR"),
                ("SECONDAR", "F1"), ("F1", "SYNGAS"), ("F1", "SEP"), ("SEP", "BIOCRUDE")]

CASES = {
    "case1": ("Case 1: HTL base case, untreated aqueous phase",
              {"AQUE": (13.1, 1.6, "product", "")}, [("SEP", "AQUE")]),
    "case2": ("Case 2: HTL + catalytic hydrothermal gasification of the aqueous phase",
              {"P80": (13.1, 1.6, "pump", "Pump"), "P160": (14.5, 1.6, "pump", "Pump"),
               "HTG": (15.9, 1.6, "reactor", "RGibbs 550 °C"), "CHTG": (17.3, 1.6, "separator", "Flash 30 °C, 1 bar"),
               "SYNGAS2": (17.3, 3.1, "product", ""), "AQUE2": (17.3, 0.3, "product", "organic-free water")},
              [("SEP", "P80"), ("P80", "P160"), ("P160", "HTG"), ("HTG", "CHTG"), ("CHTG", "SYNGAS2"), ("CHTG", "AQUE2")]),
    "case3": ("Case 3: HTL + fractional distillation of the aqueous phase",
              {"B1": (13.1, 1.6, "pump", "Heater 30 °C"), "FRACTION": (14.7, 1.6, "column", "RadFrac"),
               "VOLATILE": (14.7, 3.1, "product", "volatile organics"), "PWATER": (14.7, 0.3, "product", "pure water")},
              [("SEP", "B1"), ("B1", "FRACTION"), ("FRACTION", "VOLATILE"), ("FRACTION", "PWATER")]),
}
W, H = 1.15, 0.62


def draw(case):
    title, extra, extra_links = CASES[case]
    blocks = {**COMMON, **extra}
    links = COMMON_LINKS + extra_links
    xmax = max(x for x, *_ in blocks.values()) + 1.0
    fig, ax = plt.subplots(figsize=(1.0 * xmax, 5.6), facecolor=SURFACE)
    ax.set_xlim(-0.3, xmax)
    ax.set_ylim(-0.4, 5.3)
    ax.axis("off")
    for a, b in links:
        (x0, y0, *_), (x1, y1, *_) = blocks[a], blocks[b]
        start = (x0 + W / 2, y0) if abs(x1 - x0) > 0.1 else (x0, y0 + (H / 2 if y1 > y0 else -H / 2))
        end = (x1 - W / 2, y1) if abs(x1 - x0) > 0.1 else (x1, y1 - (H / 2 if y1 > y0 else -H / 2))
        style = "arc3,rad=0" if abs(y1 - y0) < 0.1 or abs(x1 - x0) < 0.1 else "angle,angleA=0,angleB=90,rad=0"
        if abs(x1 - x0) > 0.1 and abs(y1 - y0) > 0.1:
            end = (x1, y1 + (H / 2 if y0 > y1 else -H / 2))
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12, color=LINE, lw=1.4,
                                     connectionstyle=style, shrinkA=0, shrinkB=0))
    for name, (x, y, kind, model) in blocks.items():
        box = FancyBboxPatch((x - W / 2, y - H / 2), W, H, boxstyle="round,pad=0.02,rounding_size=0.08",
                             facecolor=KIND[kind], edgecolor=TEXT if kind not in ("feed", "product") else LINE,
                             lw=1.0 if kind not in ("feed", "product") else 0.8)
        ax.add_patch(box)
        ax.text(x, y + (0.08 if model else 0), name, ha="center", va="center", fontsize=9, fontweight="bold", color=TEXT)
        if model:
            ax.text(x, y - 0.17, model, ha="center", va="center", fontsize=6.5, color=TEXT_2)
    ax.text(-0.25, 5.2, title, fontsize=13, fontweight="bold", color=TEXT, va="top")
    ax.text(-0.25, 4.8, "Redrawn from the thesis Aspen Plus flowsheet. Property method NRTL; manure as a "
            "non-conventional component (HCOALGEN / DCOALIGT).", fontsize=8.5, color=TEXT_2, va="top")
    legend = [("Feed / product", "feed"), ("Pump / mixer / heater", "pump"), ("Reactor", "reactor"), ("Separator / column", "separator")]
    for i, (label, kind) in enumerate(legend):
        lx = xmax - 3.3 + (i % 2) * 1.6
        ly = 5.15 - (i // 2) * 0.3
        ax.add_patch(FancyBboxPatch((lx, ly - 0.09), 0.22, 0.16, boxstyle="round,pad=0.01", facecolor=KIND[kind], edgecolor=LINE, lw=0.6))
        ax.text(lx + 0.3, ly, label, fontsize=7.5, color=TEXT_2, va="center")
    path = OUT / f"flowsheet_{case}.png"
    fig.savefig(path, dpi=170, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path.name)


if __name__ == "__main__":
    for c in CASES:
        draw(c)
