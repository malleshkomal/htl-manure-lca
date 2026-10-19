"""Build the interactive findings page.

Writes docs/index.html (GitHub Pages) and site/artifact.html (body-only copy
for hosts that add their own <html>/<head>). All data and flowsheet images
are embedded, so each output is a single self-contained file.

Usage: python site/build_site.py
"""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from htlmodel import lca  # noqa: E402
from htlmodel.checks import run_checks  # noqa: E402
from htlmodel.kpis import kpi_table  # noqa: E402
from htlmodel.mass_balance import htl_balance, treatment_balance  # noqa: E402
from run import lci_table  # noqa: E402

DATA = ROOT / "data" / "thesis_tables"
SITE = Path(__file__).parent


def records(name):
    return json.loads(pd.read_csv(DATA / name).to_json(orient="records"))


def build_data():
    b = htl_balance()
    y = b.yields_dry()
    totals = lca.totals()
    t = {c: {e: {k: float(totals[(c, e, k)]) for k in lca.CATEGORIES} for e in lca.ELECTRICITY} for c in lca.CASES}
    gwp = lca.contributions().query("category == 'GWP' and case == 'case1' and electricity == 'wind'")
    share_htl = 100 * gwp.loc[gwp.contributor == "HTL conversion", "value"].sum() / gwp["value"].sum()
    air = pd.read_csv(DATA / "air_emissions_case1_wind.csv").rename(columns={
        "htl_biocrude_production": "htl", "de_diesel_mix_at_refinery": "diesel", "electricity_from_wind": "wind",
        "de_water_desalinated": "water", "eu23_heat": "heat", "euro5_truck_diesel": "truck"})
    return {
        "mass": {"manure": b.manure, "water": b.water, "biocrude": b.biocrude, "aqueous": b.aqueous, "gas": b.gas,
                 "solids": b.solids, "dry": b.dry_solids, "yieldDry": y["biocrude"], "yieldGas": y["gas"], "yieldSolids": y["solids"]},
        "treatment": {c: {"water": v["water"], "gas": v["gas_volatiles"]} for c, v in
                      ((c, treatment_balance(b.aqueous, c)) for c in ("case2", "case3"))},
        "totals": t,
        "shareHTL": share_htl,
        "lcia": json.loads(lca.contributions().to_json(orient="records")),
        "feedstock": records("manure_composition.csv"),
        "biocrude": records("biocrude_properties.csv"),
        "offgas": records("offgas_composition.csv"),
        "air": json.loads(air.to_json(orient="records")),
        "allocation": records("allocation.csv"),
        "water": records("water_footprint.csv"),
        "lci": {f"{c}_{e}": json.loads(lci_table(c, e).to_json(orient="records"))
                for c in lca.CASES for e in lca.ELECTRICITY},
        "checks": [vars(c) for c in run_checks()],
        "kpis": json.loads(kpi_table().to_json(orient="records")),
    }


def build_images():
    out = {}
    for c in lca.CASES:
        raw = (ROOT / "aspen" / f"flowsheet_{c}.png").read_bytes()
        out[c] = "data:image/png;base64," + base64.b64encode(raw).decode()
    return out


def main():
    template = (SITE / "template.html").read_text(encoding="utf-8")
    data = json.dumps(build_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = template.replace("/*__DATA__*/", data).replace("/*__IMG__*/", json.dumps(build_images()))
    (SITE / "artifact.html").write_text(page, encoding="utf-8")

    head, body = page.split('<div class="wrap"', 1)
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<meta name=\"description\" content=\"Master thesis: life cycle assessment of biocrude production from livestock manure "
            "in Germany via hydrothermal liquefaction. Interactive findings.\">\n"
            + head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
            + "<style>body { margin: 0; } [hidden] { display: none !important; } img { max-width: 100%; }</style>\n"
            "</head>\n<body>\n<div class=\"wrap\"" + body + "\n</body>\n</html>\n")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(full, encoding="utf-8")
    print(f"wrote docs/index.html ({len(full) // 1024} KB) and site/artifact.html")


if __name__ == "__main__":
    main()
