import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_api_pvt_calculate(client):
    payload = {
        "pressure_psia": 2800.0,
        "temperature_f": 190.0,
        "api_gravity": 34.0,
        "gas_gravity": 0.78,
        "correlation": "Standing"
    }
    res = await client.post("/api/v1/reservoir/pvt/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    pvt = data["value"]
    assert "Bo_rb_stb" in pvt
    assert "Bg_rb_scf" in pvt
    assert "Rs_scf_stb" in pvt
    assert "Z_factor" in pvt


@pytest.mark.asyncio
async def test_api_separator_foundation(client):
    payload = {
        "base_bo": 1.25,
        "stage_1_pressure_psia": 100.0,
        "stage_1_temperature_f": 80.0,
        "correlation_name": "UNSPECIFIED"
    }
    res = await client.post("/api/v1/reservoir/pvt/separator-foundation", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Verifies Rule 12 barrier
    assert data["status"] == "CORRELATION_SPECIFICATION_REQUIRED"


@pytest.mark.asyncio
async def test_api_chan_custom_diagnostics(client):
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    payload = {
        "well_code": "WELL-CHAN-API",
        "points": [
            {"timestamp": (t0 + timedelta(days=10)).isoformat(), "water_cut_pct": 20.0},
            {"timestamp": (t0 + timedelta(days=30)).isoformat(), "water_cut_pct": 40.0},
            {"timestamp": (t0 + timedelta(days=60)).isoformat(), "water_cut_pct": 85.0},
        ]
    }
    res = await client.post("/api/v1/reservoir/chan/diagnostics", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert "observed_pattern" in data["evidence"]
    assert len(data["evidence"]["plot_points"]) == 3


@pytest.mark.asyncio
async def test_api_darcy_flow(client):
    payload = {
        "permeability_md": 100.0,
        "thickness_ft": 40.0,
        "reservoir_pressure_psia": 4000.0,
        "flowing_bhp_psia": 3200.0,
        "viscosity_cp": 1.2,
        "bo_rb_stb": 1.22,
        "drainage_radius_ft": 1200.0,
        "wellbore_radius_ft": 0.354,
        "skin": 1.5
    }
    res = await client.post("/api/v1/reservoir/darcy/radial-flow", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert float(data["value"]) > 0


@pytest.mark.asyncio
async def test_api_productivity_index(client):
    payload = {
        "flow_rate_stbd": 800.0,
        "reservoir_pressure_psia": 3500.0,
        "flowing_bhp_psia": 3100.0
    }
    res = await client.post("/api/v1/reservoir/productivity-index", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert float(data["value"]) == 2.0  # 800 / 400 = 2.0


@pytest.mark.asyncio
async def test_api_vogel_ipr(client):
    payload = {
        "reservoir_pressure_psia": 3000.0,
        "test_rate_stbd": 700.0,
        "test_flowing_bhp_psia": 1500.0
    }
    res = await client.post("/api/v1/reservoir/vogel/ipr", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert float(data["value"]) == pytest.approx(1000.0, rel=1e-2)


@pytest.mark.asyncio
async def test_api_material_balance(client):
    payload = {
        "initial_pressure_psia": 4000.0,
        "current_pressure_psia": 3600.0,
        "initial_bo": 1.30,
        "current_bo": 1.32,
        "initial_bg": 0.00075,
        "current_bg": 0.00088,
        "initial_rs": 600.0,
        "current_rs": 570.0,
        "np_stb": 500000.0,
        "wp_stb": 25000.0,
        "rp_scf_stb": 600.0
    }
    res = await client.post("/api/v1/reservoir/material-balance/havlena-odeh", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert "F_underground_withdrawal_rb" in data["value"]


@pytest.mark.asyncio
async def test_api_vrr(client):
    payload = {
        "produced_oil_stb": 1200.0,
        "produced_water_bbl": 400.0,
        "injected_water_bbl": 1850.0,
        "bo_rb_stb": 1.25,
        "bw_rb_stb": 1.02
    }
    res = await client.post("/api/v1/reservoir/vrr", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "VALID"
    assert float(data["value"]) > 0
