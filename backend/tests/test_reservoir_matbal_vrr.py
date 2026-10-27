import pytest
from app.services.reservoir.material_balance import MaterialBalanceEngine
from app.services.reservoir.vrr_engine import VoidageReplacementEngine
from app.services.reservoir.contracts import EngineeringStatus


# -------------------------------------------------------------
# Material Balance & Havlena-Odeh Tests
# -------------------------------------------------------------

def test_material_balance_havlena_odeh_depletion_drive():
    """
    Classical textbook depletion drive reservoir case:
    Pi = 4000 psia, P = 3500 psia (delta_P = 500 psi)
    Boi = 1.30 rb/stb, Bo = 1.33 rb/stb
    Rsi = 600 scf/stb, Rs = 560 scf/stb
    Bg = 0.00090 rb/scf
    Np = 1,000,000 stb, Wp = 50,000 bbl, Bw = 1.02 rb/stb, Rp = 600 scf/stb
    Eo = (1.33 - 1.30) + (600 - 560) * 0.00090 = 0.030 + 0.036 = 0.066 rb/stb
    F = 1000000 * [1.33 + (600 - 560) * 0.00090] + 50000 * 1.02
      = 1000000 * 1.366 + 51000 = 1,417,000 res bbl
    """
    res = MaterialBalanceEngine.calculate_single_state(
        initial_pressure_psia=4000.0,
        current_pressure_psia=3500.0,
        initial_bo=1.30,
        current_bo=1.33,
        initial_bg=0.00075,
        current_bg=0.00090,
        initial_rs=600.0,
        current_rs=560.0,
        initial_swi=0.20,
        np_stb=1000000.0,
        wp_stb=50000.0,
        rp_scf_stb=600.0,
        bw_rb_stb=1.02
    )
    assert res.status == EngineeringStatus.VALID.value
    val = res.value
    assert val["Eo_oil_expansion_rb_stb"] == pytest.approx(0.066, rel=1e-2)
    assert val["F_underground_withdrawal_rb"] == pytest.approx(1417000.0, rel=1e-2)
    assert val["estimated_N_stb"] is not None
    assert val["estimated_N_stb"] > 0


def test_material_balance_missing_inputs():
    res = MaterialBalanceEngine.calculate_single_state(
        initial_pressure_psia=4000.0,
        current_pressure_psia=3500.0,
        initial_bo=1.30,
        current_bo=None,  # Missing
        initial_bg=0.00075,
        current_bg=0.00090,
        initial_rs=600.0,
        current_rs=560.0,
        initial_swi=0.20,
        np_stb=100000.0,
        wp_stb=0.0
    )
    assert res.status == EngineeringStatus.INSUFFICIENT_DATA.value


# -------------------------------------------------------------
# Voidage Replacement Ratio (VRR) Tests
# -------------------------------------------------------------

def test_vrr_balanced_injection_downhole_conversion():
    """
    Verifies that VRR performs accurate downhole PVT conversion.
    Production:
      qo = 1000 stb/d, Bo = 1.25 -> V_oil = 1250 rb
      qw = 500 bbl/d, Bw = 1.00  -> V_water = 500 rb
      Total produced res volume = 1750 res bbl.
    Water Injection:
      Wi = 1715 bbl/d, Bw = 1.02 -> V_inj = 1749.3 rb.
    VRR = 1749.3 / 1750 = ~1.00 (Balanced voidage replacement)
    """
    res = VoidageReplacementEngine.calculate_vrr(
        produced_oil_stb=1000.0,
        produced_water_bbl=500.0,
        injected_water_bbl=1715.0,
        bo_rb_stb=1.25,
        bw_rb_stb=1.02,
        bg_rb_scf=0.001,
        rs_scf_stb=400.0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert float(res.value) == pytest.approx(1.0, rel=1e-2)
    assert res.evidence["interpretation"] == "BALANCED_VOYAGE"


def test_vrr_rule_zero_withdrawal_undefined():
    """
    When total produced reservoir volume is 0, VRR must return UNDEFINED_VRR
    (division by zero strictly prevented).
    """
    res = VoidageReplacementEngine.calculate_vrr(
        produced_oil_stb=0.0,
        produced_water_bbl=0.0,
        injected_water_bbl=500.0
    )
    assert res.status == EngineeringStatus.UNDEFINED_VRR.value
    assert res.value is None
    assert "Zero total produced reservoir volume" in res.evidence["explanation"]
