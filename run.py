"""Rebuild the thesis mass balance, life cycle inventory and impact summary.

Usage: python run.py
Writes results/*.csv and prints a summary.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from htlmodel import lca  # noqa: E402
from htlmodel.checks import run_checks  # noqa: E402
from htlmodel.mass_balance import decompose, htl_balance, treatment_balance  # noqa: E402

RESULTS = ROOT / "results"

# Background processes named in the thesis (GaBi 9.1, average EU / DE datasets)
BACKGROUND = {
    "transport": "Truck, EURO 5, diesel driven (GaBi)",
    "diesel": "DE: Diesel mix at refinery (GaBi)",
    "water": "DE: Water, desalinated (GaBi)",
    "wind": "DE: Electricity from wind power (GaBi)",
    "grid": "DE: Electricity grid mix (GaBi)",
    "heat": "EU: Thermal energy (GaBi, 'EU-23: Heat')",
}


def lci_table(case, electricity):
    """Foreground inventory per 1 kg bio-oil for one scenario, from the mass balance."""
    b = htl_balance()
    per = b.per_kg_biocrude()
    tkm = per["manure"] / 1000 * 75
    rows = [
        ("Transport", "input", "manure transport, 75 km", round(tkm, 4), "t·km", BACKGROUND["transport"]),
        ("Pre-processing", "input", "wet cattle manure", round(per["manure"], 3), "kg", "farm (burden-free waste)"),
        ("Pre-processing", "input", "process water", round(per["water"], 3), "kg", BACKGROUND["water"]),
        ("Pre-processing", "input", "electricity", 0.2888, "kWh", BACKGROUND[electricity]),
        ("HTL", "input", "electricity", 0.452, "kWh", BACKGROUND[electricity]),
        ("HTL", "input", "heat", 5.01, "as printed (cal/hr)", BACKGROUND["heat"]),
        ("HTL", "output", "bio-oil (biocrude)", 1.0, "kg", "reference flow"),
        ("HTL", "output", "gas (CO2, CH4, N2, H2, H2S)", round(per["gas"], 3), "kg", "emission / off-gas"),
        ("HTL", "output", "solids (char + ash)", round(per["solids"], 3), "kg", "landfill / fertiliser"),
    ]
    if case == "case1":
        rows.append(("HTL", "output", "aqueous phase (untreated)", round(per["aqueous"], 3), "kg", "wastewater"))
    else:
        t = treatment_balance(per["aqueous"], case)
        step = "Hydrothermal gasification" if case == "case2" else "Fractional distillation"
        rows += [(step, "input", "aqueous phase", round(per["aqueous"], 3), "kg", "from HTL"),
                 (step, "output", "clean water (COD < 250 mg/L)", round(t["water"], 3), "kg", "reuse"),
                 (step, "output", "off-gas / volatile organics", round(t["gas_volatiles"], 4), "kg", "emission")]
    return pd.DataFrame(rows, columns=["stage", "direction", "flow", "amount", "unit", "provider"])


def main():
    RESULTS.mkdir(exist_ok=True)
    b = htl_balance()
    print("HTL of cattle manure, 2,000 t/day wet feed (Aspen Plus base case)")
    print(f"  in : manure {b.manure:,.1f} + water {b.water:,.1f} = {b.total_in:,.1f} kg/h")
    print(f"  out: biocrude {b.biocrude:,.1f}, aqueous {b.aqueous:,.1f}, gas {b.gas:,.1f}, solids {b.solids:,.1f} kg/h")
    print("  dry-basis yields: " + ", ".join(f"{k} {v:.1f}%" for k, v in b.yields_dry().items()))

    pd.DataFrame([{"species": k, "mass_fraction_of_wet_manure": round(v, 6)} for k, v in decompose().items()]
                 ).to_csv(RESULTS / "decompos_yields.csv", index=False)
    for case in ("case1", "case2", "case3"):
        for el in ("wind", "grid"):
            lci_table(case, el).to_csv(RESULTS / f"lci_{case}_{el}.csv", index=False)

    t = lca.totals().unstack("category")
    t.to_csv(RESULTS / "lcia_totals.csv")
    print("\nImpacts per kg bio-oil (CML 2001):")
    print(t.map(lambda v: f"{v:.3g}").to_string())

    checks = run_checks()
    pd.DataFrame([vars(c) for c in checks]).to_csv(RESULTS / "data_checks.csv", index=False)
    print(f"\nData checks: {sum(c.status == 'ok' for c in checks)} ok, {sum(c.status == 'review' for c in checks)} to review")
    print("Wrote results/*.csv")


if __name__ == "__main__":
    main()
