import pytest
from app.models.virtual_separator import SeparatorStageCondition, VirtualSeparatorConfig
from app.services.reservoir.separator_service import VirtualSeparatorService
from app.services.reservoir.contracts import EngineeringStatus


def test_virtual_separator_non_degenerate_bo_correction():
    """
    Non-degenerate fixture: Separator at 120 psia, 85 °F while stock tank is at 14.7 psia.
    Bo_corrected must be modified by the multi-stage separation process (Bo_corrected != Bo_raw).
    """
    stages = [
        SeparatorStageCondition(
            stage_index=1,
            stage_name="PRODUCTION_SEPARATOR",
            pressure_psia=120.0,
            temperature_f=85.0
        ),
        SeparatorStageCondition(
            stage_index=2,
            stage_name="STOCK_TANK",
            pressure_psia=14.7,
            temperature_f=60.0
        )
    ]

    res = VirtualSeparatorService.process_separation_train(
        total_liquid_rate_stbd=2000.0,
        water_cut_fraction=0.35,
        producing_gor_scf_stb=650.0,
        reservoir_pressure_psia=3600.0,
        reservoir_temperature_f=190.0,
        gas_gravity=0.72,
        oil_api=36.0,
        stage_conditions=stages
    )

    assert res.status == EngineeringStatus.VALID.value
    bo_raw = res.value["bo_raw"]
    bo_corrected = res.value["bo_corrected"]
    assert bo_raw > 1.0
    assert bo_corrected > 1.0
    # Provenance check: non-degenerate correction modifies Bo
    assert res.evidence["bo_comparison"]["is_modified"] is True
    assert bo_corrected != bo_raw
    assert res.value["measurement_classification"] == "VIRTUAL_ALLOCATION_ENGINEERING_ESTIMATE"
    assert "estimated_daily_avoided_cost" in res.value["economic_benchmark"]


def test_virtual_separator_degenerate_fixture():
    """
    Degenerate fixture: Single-stage separation direct to atmospheric stock tank (P_sep = P_stock).
    Bo_corrected equals Bo_raw.
    """
    stages = [
        SeparatorStageCondition(
            stage_index=1,
            stage_name="ATMOSPHERIC_BOOT",
            pressure_psia=14.7,
            temperature_f=60.0
        )
    ]
    cfg = VirtualSeparatorConfig(stock_tank_pressure_psia=14.7, stock_tank_temperature_f=60.0)

    res = VirtualSeparatorService.process_separation_train(
        total_liquid_rate_stbd=1000.0,
        water_cut_fraction=0.20,
        producing_gor_scf_stb=400.0,
        reservoir_pressure_psia=3000.0,
        reservoir_temperature_f=160.0,
        gas_gravity=0.70,
        oil_api=34.0,
        stage_conditions=stages,
        config=cfg
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["bo_raw"] == res.value["bo_corrected"]
    assert res.value["correction_factor"] == 1.0


def test_virtual_separator_three_phase_splits():
    """
    Verifies that oil, water, and gas phases are generated and conform to mass balance.
    """
    res = VirtualSeparatorService.process_separation_train(
        total_liquid_rate_stbd=1500.0,
        water_cut_fraction=0.40,
        producing_gor_scf_stb=500.0,
        reservoir_pressure_psia=3200.0,
        reservoir_temperature_f=180.0,
        gas_gravity=0.75,
        oil_api=35.0
    )
    assert res.status == EngineeringStatus.VALID.value
    # Liquid = 1500 STB/D, WC = 0.40 -> Water = 600 BPD, Oil = 900 STB/D
    assert res.value["oil_rate_stbd"] == pytest.approx(900.0, abs=1.0)
    assert res.value["water_rate_bpd"] == pytest.approx(600.0, abs=1.0)
    # Gas = 900 * 500 / 1000 = 450 MSCF/D
    assert res.value["gas_rate_mscfd"] == pytest.approx(450.0, abs=1.0)
    splits = res.evidence["phase_split"]
    assert len(splits) == 3
