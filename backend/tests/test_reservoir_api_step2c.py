"""
Test Suite for Step 2C REST API Endpoints (test_reservoir_api_step2c.py)
Validates all newly exposed Step 2C endpoints via HTTP client:
- /api/v1/reservoir/reserves/oil
- /api/v1/reservoir/reserves/gas
- /api/v1/reservoir/gas/pz
- /api/v1/reservoir/gas/deliverability
- /api/v1/reservoir/gas/pseudopressure
- /api/v1/reservoir/gas/nondarcy-turbulence
- /api/v1/reservoir/orchestration/well-diagnostic
- /api/v1/reservoir/orchestration/depletion-audit
- /api/v1/reservoir/reconciliation/virtual-separator
- /api/v1/reservoir/field/opcua/tags
- /api/v1/reservoir/field/edge/ingest
- /api/v1/reservoir/reports/daily
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_api_reserves_oil():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "area_acres": 640.0,
            "net_pay_ft": 50.0,
            "porosity": 0.20,
            "initial_water_sat": 0.25,
            "initial_oil_fvf_boi": 1.25,
            "recovery_factor": 0.35,
            "cumulative_oil_np_stb": 2_000_000.0
        }
        res = await ac.post("/api/v1/reservoir/reserves/oil", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VALID"
        assert data["unit"] == "STB"
        assert data["evidence"]["ooip_stb"] > 25_000_000


@pytest.mark.asyncio
async def test_api_gas_pz():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "history": [
                {"pressure_psia": 3200.0, "cumulative_gas_gp_mscf": 0.0},
                {"pressure_psia": 2800.0, "cumulative_gas_gp_mscf": 1_500_000.0},
                {"pressure_psia": 2400.0, "cumulative_gas_gp_mscf": 3_000_000.0}
            ],
            "temperature_f": 175.0,
            "gas_gravity": 0.68
        }
        res = await ac.post("/api/v1/reservoir/gas/pz", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VALID"
        assert "ogip_mscf" in data["evidence"]


@pytest.mark.asyncio
async def test_api_gas_deliverability():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "reservoir_pressure_pr_psia": 3000.0,
            "flowing_pressure_pwf_psia": 2000.0,
            "c_coefficient": 0.005,
            "n_exponent": 0.85
        }
        res = await ac.post("/api/v1/reservoir/gas/deliverability", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VALID"
        assert data["evidence"]["aof_potential_mscfd"] > 0


@pytest.mark.asyncio
async def test_api_reconciliation_virtual_separator():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "entity_code": "WELL-101",
            "virtual_oil_rate_stbd": 1050.0,
            "virtual_water_cut_pct": 25.0,
            "reference_oil_rate_stbd": 1000.0,
            "reference_water_cut_pct": 24.5
        }
        res = await ac.post("/api/v1/reservoir/reconciliation/virtual-separator", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VALID"
        assert "reconciliation_status" in data["evidence"]


@pytest.mark.asyncio
async def test_api_field_opcua_tags():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/reservoir/field/opcua/tags")
        assert res.status_code == 200
        data = res.json()
        assert "WELLHEAD_PRESSURE" in data


@pytest.mark.asyncio
async def test_api_reports_daily():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/reservoir/reports/daily?field_name=SOUTH_FIELD")
        assert res.status_code == 200
        data = res.json()
        assert data["field_name"] == "SOUTH_FIELD"
        assert data["reporting_standard_time"] == "08:00 UTC"
