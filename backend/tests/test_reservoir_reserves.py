"""
Test Suite for Step 2C Reserves Engine (test_reservoir_reserves.py)
Validates:
1. Volumetric STOIIP / OOIP formula: 7758 * A * h * phi * (1 - Swi) / Boi
2. Volumetric OGIP / GIIP formula: 43560 * A * h * phi * (1 - Swi) / Bgi
3. SPE-PRMS compliance: EUR = OOIP * RF, Remaining Reserves = EUR - Np
4. Non-fabrication rule: missing recovery factor returns INSUFFICIENT_DATA
5. Physical validation: out-of-range inputs reject cleanly
"""

import pytest
from app.services.reservoir.reserves_engine import ReservesEngine
from app.services.reservoir.contracts import EngineeringStatus


def test_volumetric_ooip_calculation():
    # Area = 640 acres, h = 50 ft, phi = 0.20, Swi = 0.25, Boi = 1.25 rb/STB
    # V_p = 640 * 50 * 0.20 * 0.75 = 4800 acre-ft
    # OOIP = 7758.367 * 4800 / 1.25 = 29,792,129 STB (~29.79 MMSTB)
    res = ReservesEngine.calculate_ooip_volumetric(
        area_acres=640.0,
        net_pay_ft=50.0,
        porosity=0.20,
        initial_water_sat=0.25,
        initial_oil_fvf_boi=1.25
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 29_000_000
    assert res.value < 30_500_000
    assert res.unit == "STB"
    assert "ooip_mmstb" in res.evidence
    assert res.evidence["ooip_mmstb"] == round(res.value / 1e6, 3)


def test_volumetric_giip_calculation():
    # Area = 1000 acres, h = 40 ft, phi = 0.15, Swi = 0.30, Bgi = 0.005 cuft/scf
    # HCPV = 1000 * 40 * 0.15 * 0.70 = 4200 acre-ft
    # GIIP = 43560 * 4200 / 0.005 = 36,590,400,000 scf = 36,590,400 Mscf (~36.59 Bscf)
    res = ReservesEngine.calculate_giip_volumetric(
        area_acres=1000.0,
        net_pay_ft=40.0,
        porosity=0.15,
        initial_water_sat=0.30,
        initial_gas_fvf_bgi=0.005,
        bgi_unit="cuft_scf"
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 30_000_000  # in Mscf
    assert res.unit == "Mscf"
    assert "giip_bscf" in res.evidence


def test_reserves_requires_recovery_factor_no_fabrication():
    # If recovery_factor is None, engine MUST NOT invent one
    res = ReservesEngine.calculate_oil_reserves_and_resources(
        area_acres=640.0,
        net_pay_ft=50.0,
        porosity=0.20,
        initial_water_sat=0.25,
        initial_oil_fvf_boi=1.25,
        recovery_factor=None
    )

    assert res.status == EngineeringStatus.INSUFFICIENT_DATA.value
    assert res.value is None
    assert any("Recovery factor is missing" in w or "INSUFFICIENT_DATA" in w for w in res.warnings)


def test_reserves_and_resources_partition():
    # OOIP ~ 29.79 MMSTB, RF = 0.35, Np = 5.0 MMSTB
    # EUR = 29.79 * 0.35 = 10.427 MMSTB
    # Remaining Reserves = 10.427 - 5.0 = 5.427 MMSTB
    # Unrecoverable = 29.79 - 10.427 = 19.363 MMSTB
    res = ReservesEngine.calculate_oil_reserves_and_resources(
        area_acres=640.0,
        net_pay_ft=50.0,
        porosity=0.20,
        initial_water_sat=0.25,
        initial_oil_fvf_boi=1.25,
        recovery_factor=0.35,
        cumulative_oil_np_stb=5_000_000.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 5_000_000
    assert res.evidence["eur_stb"] > res.evidence["remaining_reserves_stb"]
    assert res.evidence["unrecoverable_resources_stb"] > 0
    assert res.evidence["depletion_percentage_of_eur"] > 40.0


def test_reserves_invalid_inputs():
    # Porosity > 1.0
    res = ReservesEngine.calculate_ooip_volumetric(
        area_acres=640.0,
        net_pay_ft=50.0,
        porosity=1.5,
        initial_water_sat=0.25,
        initial_oil_fvf_boi=1.25
    )
    assert res.status == EngineeringStatus.INVALID_INPUT.value

    # Negative area
    res2 = ReservesEngine.calculate_ooip_volumetric(
        area_acres=-100.0,
        net_pay_ft=50.0,
        porosity=0.20,
        initial_water_sat=0.25,
        initial_oil_fvf_boi=1.25
    )
    assert res2.status == EngineeringStatus.INVALID_INPUT.value
