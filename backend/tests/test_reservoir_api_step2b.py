import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_api_decline(client):
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    payload = {
        "well_code": "API-DEC-01",
        "model_type": "EXPONENTIAL",
        "history": [
            {"timestamp": (t0 + timedelta(days=0)).isoformat(), "rate_stbd": 800.0},
            {"timestamp": (t0 + timedelta(days=30)).isoformat(), "rate_stbd": 750.0},
            {"timestamp": (t0 + timedelta(days=60)).isoformat(), "rate_stbd": 705.0},
        ],
        "forecast_horizon_days": 180.0
    }
    res = await client.post("/api/v1/reservoir/decline", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["qi_stbd"] > 0


@pytest.mark.asyncio
async def test_api_well_test_drawdown(client):
    payload = {
        "well_code": "API-WT-01",
        "initial_pressure_psia": 3500.0,
        "flow_rate_stbd": 200.0,
        "formation_thickness_ft": 40.0,
        "porosity_fraction": 0.20,
        "total_compressibility_psi": 1.0e-5,
        "viscosity_cp": 1.0,
        "bo_rb_stb": 1.25,
        "gauge_points": [
            {"elapsed_time_hours": 1.0, "pressure_psia": 3300.0},
            {"elapsed_time_hours": 3.0, "pressure_psia": 3260.0},
            {"elapsed_time_hours": 10.0, "pressure_psia": 3220.0},
        ]
    }
    res = await client.post("/api/v1/reservoir/well-test/drawdown", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["permeability_md"] > 0


@pytest.mark.asyncio
async def test_api_well_test_horner(client):
    payload = {
        "well_code": "API-WT-02",
        "producing_time_tp_hours": 500.0,
        "flow_rate_stbd": 250.0,
        "formation_thickness_ft": 45.0,
        "porosity_fraction": 0.22,
        "total_compressibility_psi": 1.0e-5,
        "viscosity_cp": 1.0,
        "bo_rb_stb": 1.20,
        "flowing_pwf_at_shutin_psia": 3000.0,
        "gauge_points": [
            {"elapsed_time_hours": 1.0, "pressure_psia": 3200.0},
            {"elapsed_time_hours": 4.0, "pressure_psia": 3300.0},
            {"elapsed_time_hours": 16.0, "pressure_psia": 3380.0},
        ]
    }
    res = await client.post("/api/v1/reservoir/well-test/horner", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"


@pytest.mark.asyncio
async def test_api_aquifer(client):
    payload = {
        "model_type": "FETKOVICH",
        "initial_pressure_psia": 4000.0,
        "permeability_md": 100.0,
        "formation_thickness_ft": 50.0,
        "porosity_fraction": 0.20,
        "total_compressibility_psi": 7.0e-6,
        "water_viscosity_cp": 0.50,
        "reservoir_radius_ft": 2000.0,
        "aquifer_radius_ft": 10000.0,
        "pressure_history": [
            {"time_days": 0.0, "reservoir_pressure_psia": 4000.0},
            {"time_days": 60.0, "reservoir_pressure_psia": 3850.0},
            {"time_days": 120.0, "reservoir_pressure_psia": 3700.0},
        ]
    }
    res = await client.post("/api/v1/reservoir/aquifer", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["cumulative_water_influx_rb"] > 0


@pytest.mark.asyncio
async def test_api_fractional_flow(client):
    payload = {
        "sw_connate": 0.20,
        "so_residual": 0.25,
        "water_viscosity_cp": 0.5,
        "oil_viscosity_cp": 2.0
    }
    res = await client.post("/api/v1/reservoir/fractional-flow", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"


@pytest.mark.asyncio
async def test_api_buckley_leverett(client):
    payload = {
        "injection_rate_bpd": 1000.0,
        "cross_sectional_area_ft2": 20000.0,
        "length_between_wells_ft": 1500.0,
        "porosity_fraction": 0.20,
        "initial_water_saturation": 0.20,
        "so_residual": 0.25,
        "water_viscosity_cp": 0.50,
        "oil_viscosity_cp": 2.0
    }
    res = await client.post("/api/v1/reservoir/buckley-leverett", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["shock_front_saturation_swf"] > 0


@pytest.mark.asyncio
async def test_api_waterflood(client):
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    payload = {
        "injector_well_code": "INJ-API-01",
        "history": [
            {"timestamp": (t0 + timedelta(days=0)).isoformat(), "injection_rate_bpd": 800.0, "offset_oil_rate_stbd": 400.0, "offset_water_rate_bpd": 100.0},
            {"timestamp": (t0 + timedelta(days=30)).isoformat(), "injection_rate_bpd": 850.0, "offset_oil_rate_stbd": 420.0, "offset_water_rate_bpd": 120.0},
        ]
    }
    res = await client.post("/api/v1/reservoir/waterflood", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert "canonical_vrr" in data["value"]


@pytest.mark.asyncio
async def test_api_sweep(client):
    payload = {
        "sw_connate": 0.20,
        "so_residual": 0.25,
        "areal_sweep_ea": 0.80,
        "vertical_sweep_ei": 0.70
    }
    res = await client.post("/api/v1/reservoir/sweep", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["volumetric_sweep_efficiency_Ev"] == 0.56


@pytest.mark.asyncio
async def test_api_virtual_separator(client):
    payload = {
        "total_liquid_rate_stbd": 1200.0,
        "water_cut_fraction": 0.30,
        "producing_gor_scf_stb": 500.0,
        "reservoir_pressure_psia": 3200.0,
        "reservoir_temperature_f": 180.0,
        "gas_gravity": 0.75,
        "oil_api": 35.0
    }
    res = await client.post("/api/v1/reservoir/virtual-separator", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["measurement_classification"] == "VIRTUAL_ALLOCATION_ENGINEERING_ESTIMATE"


@pytest.mark.asyncio
async def test_api_well_allocation(client):
    payload = {
        "choke_inputs": {
            "wellhead_pressure_psia": 750.0,
            "choke_size_64ths": 32.0,
            "producing_gor_scf_stb": 550.0,
            "calibrated_wc_fraction": 0.25,
            "correlation_name": "GILBERT"
        }
    }
    res = await client.post("/api/v1/reservoir/well-allocation", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["allocated_oil_rate_stbd"] > 0


@pytest.mark.asyncio
async def test_api_wc_calibration(client):
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    payload = {
        "lab_sample": {
            "sample_id": "LAB-01",
            "timestamp": t0.isoformat(),
            "well_code": "WELL-01",
            "water_cut_value": 28.0,
            "is_percentage": True
        },
        "live_sample_reading": {
            "timestamp": t0.isoformat(),
            "well_code": "WELL-01",
            "water_cut_value": 24.0,
            "is_percentage": True
        }
    }
    res = await client.post("/api/v1/reservoir/wc-calibration", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert data["value"]["calibration_factor"] > 1.0


@pytest.mark.asyncio
async def test_api_integration_connectors(client):
    res = await client.get("/api/v1/reservoir/integration/connectors")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 3
    for conn in data:
        # Strictly inactive in Step 2B
        assert conn["is_live_connection_active"] is False
