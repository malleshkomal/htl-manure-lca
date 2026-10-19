import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from htlmodel import lca  # noqa: E402
from htlmodel.mass_balance import (ASPEN_CASE1, ASPEN_CASE2, ASPEN_CASE3,  # noqa: E402
                                   channiwala_hhv, decompose, htl_balance, treatment_balance)


def test_base_case_reproduces_aspen_mass_balance():
    b = htl_balance()
    for k in ("manure", "water", "biocrude", "solids", "gas"):
        assert getattr(b, k) == pytest.approx(ASPEN_CASE1[k], abs=0.01)
    assert b.aqueous == pytest.approx(ASPEN_CASE1["aqueous"], abs=0.1)


def test_mass_balance_closes_at_any_feed_rate():
    for feed in (500, 2000, 5000):
        b = htl_balance(feed)
        assert b.total_out == pytest.approx(b.total_in)


def test_slurry_is_twenty_percent_solids():
    b = htl_balance()
    assert b.dry_solids / b.total_in == pytest.approx(0.20)


def test_dry_basis_biocrude_yield_matches_table_4_2_3():
    assert htl_balance().yields_dry()["biocrude"] == pytest.approx(27.61, abs=0.01)


def test_per_kg_inventory_matches_table_4_4_where_consistent():
    per = htl_balance().per_kg_biocrude()
    assert per["manure"] == pytest.approx(17.1, abs=0.06)
    assert per["water"] == pytest.approx(1.1, abs=0.05)
    assert per["solids"] == pytest.approx(0.89491, abs=0.001)


def test_decompos_yields_sum_to_one_with_sulfur():
    assert sum(decompose().values()) == pytest.approx(1.0, abs=1e-4)
    assert sum(decompose(include_sulfur=False).values()) < 0.999


def test_aqueous_treatment_reproduces_case_2_and_3():
    c2 = treatment_balance(ASPEN_CASE2["in"], "case2")
    assert c2["water"] == pytest.approx(ASPEN_CASE2["organic_free_water"], rel=1e-6)
    c3 = treatment_balance(ASPEN_CASE3["in"], "case3")
    assert c3["water"] == pytest.approx(ASPEN_CASE3["pure_water"], rel=1e-6)


def test_harmonised_impacts_reproduce_printed_totals():
    t, p = lca.totals(), lca.printed_totals()
    assert ((t / p - 1).abs() < 0.005).all()


def test_wind_beats_grid_in_every_case_and_category():
    t = lca.totals()
    for case in lca.CASES:
        for cat in lca.CATEGORIES:
            assert t[(case, "wind", cat)] < t[(case, "grid", cat)]


def test_htl_conversion_dominates_gwp():
    shares = lca.shares("GWP")
    assert (shares["HTL conversion"] > 60).all()


def test_channiwala_formula():
    # 1 kg of pure carbon: 34.91 MJ/kg
    assert channiwala_hhv(100, 0, 0) == pytest.approx(34.91)
