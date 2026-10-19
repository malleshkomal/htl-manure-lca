"""Mass balance of hydrothermal liquefaction (HTL) of cattle manure.

Re-implements the bookkeeping of the thesis's Aspen Plus flowsheets in
Python so the numbers can be checked and re-run without Aspen:

* ``decompose`` is the DECOMPOS RYield block (Fortran calculator of
  Table 3.2.1): wet manure -> H2O, char, ash, O2, H2, N2, C (and S).
* ``htl_balance`` scales the HTL product split reported by Aspen
  (Table 4.2.1) to any feed rate and slurry concentration.
* ``treatment_balance`` splits the aqueous phase for case 2 (catalytic
  hydrothermal gasification) and case 3 (fractional distillation).

This is not a thermodynamic simulation: product yields come from the
Aspen results, not from RGibbs equilibrium.
"""

from dataclasses import dataclass

# Table 3.1 (ultimate analysis on a dry basis, proximate analysis)
ULTANAL = {"ash": 17.572, "C": 38.831, "H": 5.638, "N": 5.68, "S": 1.05, "O": 31.215}
PROXANAL = {"moisture": 78.76, "fixed_carbon": 18.643, "volatile_matter": 63.784, "ash": 17.572}

# Aspen Plus results for case 1 (Table 4.2.1), kg/h
ASPEN_CASE1 = {"manure": 83333.33, "water": 5166.66, "biocrude": 4887.52,
               "aqueous": 70684.54408, "solids": 4373.91, "gas": 8554.01}
# Aqueous-phase treatment results (Table 4.2.1), kg/h
ASPEN_CASE2 = {"in": 70677.51, "organic_free_water": 70013.04, "gas_volatiles": 664.474}
ASPEN_CASE3 = {"in": 70684.54408, "pure_water": 70259.5, "gas_volatiles": 425.0}


def decompose(moisture=PROXANAL["moisture"], ult=ULTANAL, prox=PROXANAL, include_sulfur=True):
    """DECOMPOS yields (mass fraction of wet manure), as in the Fortran calculator.

    FACT = (100 - WATER) / 100; H2O = WATER / 100; CHAR = PROX(FC) * FACT;
    ASH, O2, H2, N2 = ULT(...) * FACT; C = ULT(C) * FACT - CHAR.
    The printed code has no sulfur line; with ``include_sulfur`` the S
    fraction is added so the yields sum to 1.
    """
    fact = (100 - moisture) / 100
    y = {
        "H2O": moisture / 100,
        "CHAR": prox["fixed_carbon"] / 100 * fact,
        "ASH": ult["ash"] / 100 * fact,
        "O2": ult["O"] / 100 * fact,
        "H2": ult["H"] / 100 * fact,
        "N2": ult["N"] / 100 * fact,
    }
    y["C"] = ult["C"] / 100 * fact - y["CHAR"]
    if include_sulfur:
        y["S"] = ult["S"] / 100 * fact
    return y


@dataclass
class HTLBalance:
    manure: float
    water: float
    dry_solids: float
    biocrude: float
    solids: float
    gas: float
    aqueous: float

    @property
    def total_in(self):
        return self.manure + self.water

    @property
    def total_out(self):
        return self.biocrude + self.solids + self.gas + self.aqueous

    def yields_dry(self):
        """Product yields on a dry-feed basis (thesis Eq. 3), %."""
        return {k: 100 * getattr(self, k) / self.dry_solids for k in ("biocrude", "solids", "gas")}

    def per_kg_biocrude(self):
        return {k: getattr(self, k) / self.biocrude
                for k in ("manure", "water", "biocrude", "solids", "gas", "aqueous")}


def htl_balance(feed_t_per_day=2000.0, moisture=PROXANAL["moisture"], slurry_solids=0.20):
    """HTL mass balance in kg/h for a wet-manure feed rate.

    Water is added to reach ``slurry_solids`` dry matter. Biocrude, solids
    and gas use the dry-basis yields of the Aspen case 1 result; the
    aqueous phase is the remainder, so the balance closes by construction.
    """
    manure = feed_t_per_day * 1000 / 24
    dry = manure * (1 - moisture / 100)
    water = max(dry / slurry_solids - manure, 0.0)

    ref_dry = ASPEN_CASE1["manure"] * (1 - PROXANAL["moisture"] / 100)
    biocrude = dry * ASPEN_CASE1["biocrude"] / ref_dry
    solids = dry * ASPEN_CASE1["solids"] / ref_dry
    gas = dry * ASPEN_CASE1["gas"] / ref_dry
    aqueous = manure + water - biocrude - solids - gas
    return HTLBalance(manure, water, dry, biocrude, solids, gas, aqueous)


def treatment_balance(aqueous, case):
    """Split an aqueous stream (kg/h) by the case 2 or case 3 Aspen result."""
    ref = ASPEN_CASE2 if case == "case2" else ASPEN_CASE3
    gas = aqueous * ref["gas_volatiles"] / ref["in"]
    return {"water": aqueous - gas, "gas_volatiles": gas}


def channiwala_hhv(c, h, o, n=0.0, s=0.0, ash=0.0):
    """Higher heating value (MJ/kg) from mass percentages, thesis Eq. 2 (Channiwala & Parikh)."""
    return (34.91 * c + 117.83 * h - 10.34 * o - 1.51 * n + 10.05 * s - 2.11 * ash) / 100
