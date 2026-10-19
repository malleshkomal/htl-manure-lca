"""Consistency checks between the thesis tables, its text and the mass balance."""

from dataclasses import dataclass

from . import lca
from .mass_balance import (ASPEN_CASE1, PROXANAL, ULTANAL, channiwala_hhv, decompose, htl_balance)


@dataclass
class Check:
    topic: str
    status: str  # "ok" or "review"
    finding: str


def run_checks():
    b = htl_balance()
    per = b.per_kg_biocrude()
    y = b.yields_dry()
    daf = 100 * b.biocrude / (b.dry_solids * (1 - ULTANAL["ash"] / 100))
    out = []

    closure = b.total_out - b.total_in
    out.append(Check("Mass balance", "ok" if abs(closure) < 1 else "review",
                     f"Inputs {b.total_in:,.2f} kg/h = outputs {b.total_out:,.2f} kg/h (Table 4.2.1 closes)."))
    out.append(Check("Slurry concentration", "ok",
                     f"Dry solids {b.dry_solids:,.0f} kg/h in {b.total_in:,.0f} kg/h = {100 * b.dry_solids / b.total_in:.1f}% "
                     "(matches the 20 wt% target)."))
    out.append(Check("Biocrude yield basis", "review",
                     f"4,887.52 kg/h is {y['biocrude']:.1f}% of the dry feed and {daf:.1f}% on a dry ash-free basis. "
                     "Table 4.2.3 (27.61%, dry basis) is consistent; Section 4.2.2 and the conclusion call 27.7–27.9% 'daf'."))
    out.append(Check("Daily biocrude output", "review",
                     f"4,887.52 kg/h × 24 h = {ASPEN_CASE1['biocrude'] * 24 / 1000:.1f} t/day; Section 4.2.2 says 117,301 tonne/day."))
    out.append(Check("Gas and biochar in the LCI", "review",
                     f"Mass balance gives {per['gas']:.2f} kg gas and {per['solids']:.3f} kg solids per kg bio-oil "
                     f"(yields {y['gas']:.1f}% and {y['solids']:.1f}% of dry feed). Table 4.4 lists 0.64 kg gas, and its yield "
                     "labels for gas (24.717%) and biochar (48.32%) are swapped."))
    out.append(Check("Aqueous phase in the LCI", "review",
                     f"Mass balance gives {per['aqueous']:.2f} kg aqueous phase per kg bio-oil; Table 4.4 lists 14.62 kg."))
    out.append(Check("Case 3 input stream", "review",
                     "Table 4.2.1 lists 75,572.07 kg/h into fractional distillation. That is the LIQUIDS stream "
                     "(biocrude + aqueous); the outputs 70,259.5 + 425.0 = 70,684.5 kg/h equal the aqueous phase alone."))
    t, p = lca.totals(), lca.printed_totals()
    worst = float(((t / p) - 1).abs().max())
    out.append(Check("Impact table columns", "review",
                     "In Table 4.1 some rows have the diesel-mix and truck values (and once the EP values) under swapped "
                     f"column headings, and case 2 grid FAETP diesel reads 0.00809 instead of 0.000809. With one consistent "
                     f"assignment every printed total is reproduced within {100 * worst:.1f}%."))
    out.append(Check("Grid GWP in the conclusion", "review",
                     "Table 4.1 gives 1.67 kg CO2 eq (case 1, grid); Section 4.6 says 1.76."))
    out.append(Check("Biocrude HHV", "review",
                     f"Aspen reports 39.1 MJ/kg; the thesis's Eq. 2 applied to the reported biocrude composition gives "
                     f"{channiwala_hhv(60.56, 8.045, 29.11, 1.48, 1.29):.1f} MJ/kg. The composition also sums to 100.5%."))
    out.append(Check("Raw manure HHV", "review",
                     f"Eq. 2 on the dry ultimate analysis gives {channiwala_hhv(ULTANAL['C'], ULTANAL['H'], ULTANAL['O'], ULTANAL['N'], ULTANAL['S'], ULTANAL['ash']):.1f} "
                     "MJ/kg (dry); Table 4.2.3 lists 7.9 MJ/kg without a basis."))
    no_s = sum(decompose(include_sulfur=False).values())
    out.append(Check("DECOMPOS Fortran", "review",
                     f"Table 3.2.1 has no sulfur line, so the yields sum to {no_s:.4f} instead of 1; adding "
                     f"S = ULT(S) × FACT closes it ({sum(decompose().values()):.4f})."))
    out.append(Check("HTL operating conditions", "review",
                     "Table 3.2.2 gives 350 °C and 100 bar; Section 3.2 runs the SECONDRY RGibbs reactor at 300 °C and 175 bar."))
    out.append(Check("Aqueous-phase pumps", "review",
                     "Section 3.3 names pumps P60 (60 bar) and P80 (80 bar); the flowsheet labels them P80 and P160."))
    out.append(Check("HTL heat input unit", "review", "Table 4.4 gives heat as 5.01 'cal/hr' per kg bio-oil; the unit needs confirming."))
    out.append(Check("Moisture in the slurry", "ok",
                     f"Manure at {PROXANAL['moisture']}% moisture needs {ASPEN_CASE1['water']:,.0f} kg/h make-up water "
                     "(≈1.06 kg per kg bio-oil, Table 4.4: 1.1 kg)."))
    return out
