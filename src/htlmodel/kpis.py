"""KPI framework for the HTL-of-manure results.

Four pillars: process performance, climate and environment, water and
circularity, and data quality. Each KPI has a definition, a formula, a
direction (higher or lower is better), a benchmark where one exists, and a
status per scenario: "pass", "watch" or "fail" against that benchmark, or
"info" when there is nothing to compare against.
"""

import pandas as pd

from . import lca
from .mass_balance import ULTANAL, channiwala_hhv, htl_balance, treatment_balance

SCENARIOS = [(c, e) for c in lca.CASES for e in lca.ELECTRICITY]
BIOCRUDE_HHV = 39.1  # MJ/kg, Aspen Plus result (thesis Section 4.2.1)
BIOCRUDE = {"C": 60.56, "N": 1.48}  # wt%, thesis Table 4.2.3
LIT_YIELD = (19.05, 30.2)  # % dry basis, manure HTL studies in thesis Table 4.2.3
LIT_HHV = (34.7, 35.53)  # MJ/kg, same studies
FOSSIL_COMPARATOR = 94.0  # g CO2 eq/MJ, RED II (EU 2018/2001) transport fuel comparator
RED_THRESHOLDS = (65.0, 50.0)  # % saving: plants from 2021 / plants before Oct 2015
COD_LIMIT = 250  # mg/L, thesis target for reusable water


def _row(pillar, kpi, unit, direction, definition, formula, values, status, benchmark="", source=""):
    """values/status: a scalar for all scenarios, or a dict keyed by (case, electricity)."""
    r = {"pillar": pillar, "kpi": kpi, "unit": unit, "direction": direction, "definition": definition,
         "formula": formula, "benchmark": benchmark, "benchmark_source": source}
    for s in SCENARIOS:
        key = f"{s[0]}_{s[1]}"
        r[key] = values[s] if isinstance(values, dict) else values
        r[key + "_status"] = status[s] if isinstance(status, dict) else status
    return r


def ghg_saving(gwp_per_kg):
    """Indicative saving vs the RED II fossil comparator, % (HHV basis, cradle to gate)."""
    per_mj = 1000 * gwp_per_kg / BIOCRUDE_HHV
    return 100 * (1 - per_mj / FOSSIL_COMPARATOR)


def red_status(saving):
    return "pass" if saving >= RED_THRESHOLDS[0] else "watch" if saving >= RED_THRESHOLDS[1] else "fail"


def kpi_table():
    b = htl_balance()
    y = b.yields_dry()
    t = lca.totals()
    rows = []

    # Process performance
    rows.append(_row("Process performance", "Biocrude yield", "% of dry feed", "higher",
                     "Biocrude produced per unit of dry manure fed to the reactor.", "m_biocrude / m_dry_feed",
                     y["biocrude"], "pass" if LIT_YIELD[0] <= y["biocrude"] else "fail",
                     f"{LIT_YIELD[0]}–{LIT_YIELD[1]}% in manure HTL studies", "Thesis Table 4.2.3 [34–36]"))
    rows.append(_row("Process performance", "Biocrude output", "t/day", "higher",
                     "Biocrude production of the 2,000 t/day plant.", "m_biocrude × 24 h", b.biocrude * 24 / 1000, "info"))
    rows.append(_row("Process performance", "Biocrude heating value", "MJ/kg", "higher",
                     "Higher heating value of the biocrude from Aspen Plus.", "Aspen Plus stream HHV", BIOCRUDE_HHV,
                     "pass" if BIOCRUDE_HHV >= LIT_HHV[0] else "fail",
                     f"{LIT_HHV[0]}–{LIT_HHV[1]} MJ/kg in manure HTL studies", "Thesis Table 4.2.3 [34–36]"))
    feed_hhv = channiwala_hhv(ULTANAL["C"], ULTANAL["H"], ULTANAL["O"], ULTANAL["N"], ULTANAL["S"], ULTANAL["ash"])
    er = 100 * b.biocrude * BIOCRUDE_HHV / (b.dry_solids * feed_hhv)
    rows.append(_row("Process performance", "Energy recovery in biocrude", "%", "higher",
                     "Share of the dry manure's chemical energy that ends up in the biocrude.",
                     "m_biocrude × HHV_biocrude / (m_dry × HHV_dry manure)", er, "info",
                     f"Dry manure HHV {feed_hhv:.1f} MJ/kg from thesis Eq. 2", "Channiwala & Parikh (2002)"))
    c_rec = 100 * b.biocrude * BIOCRUDE["C"] / (b.dry_solids * ULTANAL["C"])
    rows.append(_row("Process performance", "Carbon recovery in biocrude", "% of feed C", "higher",
                     "Share of the manure's carbon that ends up in the biocrude.", "m_biocrude × C_biocrude / (m_dry × C_manure)",
                     c_rec, "info"))
    n_frac = 100 * b.biocrude * BIOCRUDE["N"] / (b.dry_solids * ULTANAL["N"])
    rows.append(_row("Process performance", "Nitrogen carried into biocrude", "% of feed N", "lower",
                     "Share of the manure's nitrogen left in the oil. Less nitrogen means less NOx and easier upgrading.",
                     "m_biocrude × N_biocrude / (m_dry × N_manure)", n_frac, "info"))

    # Climate and environment
    gwp = {s: float(t[(s[0], s[1], "GWP")]) for s in SCENARIOS}
    rows.append(_row("Climate & environment", "Climate impact per kg", "kg CO₂ eq/kg", "lower",
                     "Cradle-to-gate GWP100 per kg of bio-oil (CML 2001).", "Σ contributions, GaBi", gwp, "info"))
    per_mj = {s: 1000 * v / BIOCRUDE_HHV for s, v in gwp.items()}
    rows.append(_row("Climate & environment", "Climate impact per MJ", "g CO₂ eq/MJ", "lower",
                     "GWP per unit of fuel energy, so the oil can be compared with other fuels.", "1000 × GWP / HHV",
                     per_mj, {s: "pass" if v < FOSSIL_COMPARATOR else "fail" for s, v in per_mj.items()},
                     f"Fossil comparator {FOSSIL_COMPARATOR:g} g CO₂ eq/MJ", "RED II, Directive (EU) 2018/2001"))
    sav = {s: ghg_saving(v) for s, v in gwp.items()}
    rows.append(_row("Climate & environment", "Indicative GHG saving vs fossil fuel", "%", "higher",
                     "Saving against the fossil comparator. Indicative only: cradle to gate, HHV basis, biogenic CO₂ counted.",
                     "1 − (g CO₂ eq/MJ) / 94", sav, {s: red_status(v) for s, v in sav.items()},
                     "≥ 65% for new plants (pass), ≥ 50% for older plants (watch)", "RED II Art. 29(10)"))
    share = lca.shares("GWP")
    rows.append(_row("Climate & environment", "Conversion share of climate impact", "% of GWP", "info",
                     "How much of the GWP comes from the HTL conversion step: the hotspot to improve.",
                     "GWP_HTL / GWP_total", {s: float(share.loc[s, "HTL conversion"]) for s in SCENARIOS}, "info"))
    for cat, unit, name in (("AP", "g SO₂ eq/kg", "Acidification per kg"), ("EP", "g PO₄ eq/kg", "Eutrophication per kg"),
                            ("FAETP", "g DCB eq/kg", "Freshwater ecotoxicity per kg")):
        vals = {s: 1000 * float(t[(s[0], s[1], cat)]) for s in SCENARIOS}
        status = {s: "pass" if s[1] == "wind" else "watch" for s in SCENARIOS}
        rows.append(_row("Climate & environment", name, unit, "lower", f"{lca.CATEGORIES[cat]} per kg bio-oil (CML 2001).",
                         "Σ contributions, GaBi", vals, status, "Wind-electricity result of the same case",
                         "Thesis Table 4.1"))

    # Water and circularity
    rec = {}
    for s in SCENARIOS:
        rec[s] = 0.0 if s[0] == "case1" else 100 * treatment_balance(b.aqueous, s[0])["water"] / b.aqueous
    rows.append(_row("Water & circularity", "Water recovered from the aqueous phase", "%", "higher",
                     "Share of the HTL aqueous phase returned as clean water.", "m_clean water / m_aqueous", rec,
                     {s: "pass" if v >= 99 else "fail" for s, v in rec.items()}, "≥ 99%", "Thesis Sections 3.3–3.4"))
    cod = {s: "untreated" if s[0] == "case1" else f"< {COD_LIMIT}" for s in SCENARIOS}
    rows.append(_row("Water & circularity", "COD of discharged water", "mg/L", "lower",
                     "Chemical oxygen demand of the water leaving the plant.", "Aspen Plus / literature", cod,
                     {s: "fail" if s[0] == "case1" else "pass" for s in SCENARIOS},
                     f"< {COD_LIMIT} mg/L for reuse; untreated HTL water 41,000–77,000 mg/L", "Thesis Sections 3.4, 3.5.2 [103]"))
    valorised = 100 * (b.biocrude + b.solids) / b.dry_solids
    rows.append(_row("Water & circularity", "Dry feed turned into products", "% of dry feed", "higher",
                     "Biocrude plus biochar per unit of dry manure: the mass that leaves as a usable product.",
                     "(m_biocrude + m_solids) / m_dry", valorised, "info"))
    rows.append(_row("Water & circularity", "Value share of biocrude", "% (economic allocation)", "higher",
                     "Share of the product value carried by the biocrude.", "price × mass, Table 4.4.2", 69.0, "info",
                     "Biocrude 400 €/t, biochar 200 €/t", "Thesis Table 4.4.2"))
    blue = {s: 89.7 if s[1] == "wind" else 39.64 for s in SCENARIOS}
    rows.append(_row("Water & circularity", "Blue water from pre-processing", "% of blue water", "info",
                     "Share of blue-water consumption that comes from pre-processing.", "GaBi water footprint", blue, "info",
                     "", "Thesis Table 4.5"))

    # Data quality
    closure = 100 * b.total_out / b.total_in
    rows.append(_row("Data quality", "Mass balance closure", "%", "target",
                     "Outputs divided by inputs in the Aspen Plus base case.", "Σ m_out / Σ m_in", closure,
                     "pass" if abs(closure - 100) < 0.1 else "fail", "100 ± 0.1%"))
    p = lca.printed_totals()
    dev = float(((t / p) - 1).abs().max() * 100)
    rows.append(_row("Data quality", "Impact totals reproduced", "max deviation, %", "lower",
                     "Largest difference between recomputed and printed impact totals.", "max |recomputed / printed − 1|",
                     dev, "pass" if dev < 1 else "watch", "< 1%"))
    return pd.DataFrame(rows)


def scorecard():
    """Count of pass / watch / fail per scenario."""
    k = kpi_table()
    out = {}
    for c, e in SCENARIOS:
        st = k[f"{c}_{e}_status"]
        out[f"{c}_{e}"] = {s: int((st == s).sum()) for s in ("pass", "watch", "fail", "info")}
    return pd.DataFrame(out).T
