"""Life cycle impact results per kg of bio-oil (CML 2001, GaBi 9.1 background)."""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "thesis_tables"

CASES = {"case1": "Case 1: HTL base case", "case2": "Case 2: HTL + hydrothermal gasification",
         "case3": "Case 3: HTL + fractional distillation"}
ELECTRICITY = {"wind": "Wind electricity", "grid": "German grid mix"}
CATEGORIES = {"GWP": "Global warming potential", "AP": "Acidification potential",
              "EP": "Eutrophication potential", "FAETP": "Freshwater aquatic ecotoxicity"}


def contributions():
    """Harmonised contributions: one row per case, electricity, category and contributor."""
    return pd.read_csv(DATA / "lcia_contributions.csv")


def printed_totals():
    """Totals as printed in thesis Table 4.1."""
    t = pd.read_csv(DATA / "lcia_table_4_1_as_printed.csv")
    return t.set_index(["case", "electricity", "category"])["total"]


def totals():
    """Totals recomputed from the harmonised contributions."""
    return contributions().groupby(["case", "electricity", "category"])["value"].sum()


def shares(category):
    """Percentage contribution of each contributor, per scenario, for one category."""
    c = contributions()
    c = c[c["category"] == category]
    pivot = c.pivot_table(index=["case", "electricity"], columns="contributor", values="value", aggfunc="sum").fillna(0)
    return pivot.div(pivot.sum(axis=1), axis=0) * 100
