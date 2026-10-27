import pytest
from app.services.reservoir.aquifer_engine import AquiferEngine, AquiferPressureStep
from app.services.reservoir.contracts import EngineeringStatus


def test_aquifer_fetkovich_mandatory_model():
    """
    Standard Fetkovich (1971) finite radial aquifer test.
    pi = 4000 psia, ra = 15000 ft, r0 = 3000 ft, h = 100 ft, phi = 0.22, ct = 8e-6, mu = 0.5 cp, k = 150 md.
    """
    steps = [
        AquiferPressureStep(time_days=0.0, reservoir_pressure_psia=4000.0),
        AquiferPressureStep(time_days=90.0, reservoir_pressure_psia=3850.0),
        AquiferPressureStep(time_days=180.0, reservoir_pressure_psia=3720.0),
        AquiferPressureStep(time_days=365.0, reservoir_pressure_psia=3580.0),
    ]

    res = AquiferEngine.calculate_fetkovich(
        pressure_history=steps,
        initial_pressure_psia=4000.0,
        permeability_md=150.0,
        formation_thickness_ft=100.0,
        porosity_fraction=0.22,
        total_compressibility_psi=8.0e-6,
        water_viscosity_cp=0.50,
        reservoir_radius_ft=3000.0,
        aquifer_radius_ft=15000.0,
        encroachment_angle_deg=360.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["cumulative_water_influx_rb"] > 0
    assert res.value["maximum_encroachable_water_wei_rb"] > res.value["cumulative_water_influx_rb"]
    assert res.value["aquifer_productivity_index_j_aq"] > 0
    assert len(res.evidence["step_history"]) == 3


def test_aquifer_schilthuis_steady_state():
    """
    Tests Schilthuis steady-state model: We = C * sum(Delta P * dt)
    """
    steps = [
        AquiferPressureStep(time_days=0.0, reservoir_pressure_psia=3500.0),
        AquiferPressureStep(time_days=30.0, reservoir_pressure_psia=3300.0),
        AquiferPressureStep(time_days=60.0, reservoir_pressure_psia=3100.0),
    ]

    res = AquiferEngine.calculate_schilthuis(
        pressure_history=steps,
        initial_pressure_psia=3500.0,
        water_influx_constant_c_stb_day_psi=5.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["cumulative_water_influx_rb"] > 0


def test_aquifer_van_everdingen_hurst_unsteady_state():
    """
    Tests Van Everdingen & Hurst radial unsteady-state model.
    """
    steps = [
        AquiferPressureStep(time_days=0.0, reservoir_pressure_psia=3800.0),
        AquiferPressureStep(time_days=100.0, reservoir_pressure_psia=3650.0),
        AquiferPressureStep(time_days=200.0, reservoir_pressure_psia=3500.0),
    ]

    res = AquiferEngine.calculate_van_everdingen_hurst(
        pressure_history=steps,
        initial_pressure_psia=3800.0,
        permeability_md=80.0,
        formation_thickness_ft=60.0,
        porosity_fraction=0.18,
        total_compressibility_psi=7.0e-6,
        water_viscosity_cp=0.45,
        reservoir_radius_ft=2500.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["cumulative_water_influx_rb"] > 0


def test_aquifer_invalid_geometry_and_insufficient_data():
    """
    Verifies rejection when aquifer radius <= reservoir radius, or steps < 2.
    """
    steps = [AquiferPressureStep(time_days=0.0, reservoir_pressure_psia=4000.0)]
    res_few = AquiferEngine.calculate_fetkovich(
        pressure_history=steps,
        initial_pressure_psia=4000.0,
        permeability_md=100.0,
        formation_thickness_ft=50.0,
        porosity_fraction=0.20,
        total_compressibility_psi=7e-6,
        water_viscosity_cp=0.5,
        reservoir_radius_ft=2000.0,
        aquifer_radius_ft=10000.0
    )
    assert res_few.status == EngineeringStatus.INSUFFICIENT_DATA.value

    steps2 = [
        AquiferPressureStep(time_days=0.0, reservoir_pressure_psia=4000.0),
        AquiferPressureStep(time_days=50.0, reservoir_pressure_psia=3900.0),
    ]
    res_geom = AquiferEngine.calculate_fetkovich(
        pressure_history=steps2,
        initial_pressure_psia=4000.0,
        permeability_md=100.0,
        formation_thickness_ft=50.0,
        porosity_fraction=0.20,
        total_compressibility_psi=7e-6,
        water_viscosity_cp=0.5,
        reservoir_radius_ft=5000.0,
        aquifer_radius_ft=4000.0  # ra < r0!
    )
    assert res_geom.status == EngineeringStatus.INVALID_INPUT.value
