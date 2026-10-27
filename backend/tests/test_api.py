import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_wells_crud_and_config_update(client):
    # 1. Create well
    well_payload = {
        "well_code": "WELL-API-01",
        "field_name": "Rub Al-Khali Field",
        "status": "ACTIVE",
        "config": {
            "wc_threshold": 78.0,
            "wc_trend_window_hours": 48,
            "alert_cooldown_minutes": 30,
            "surveillance_interval_minutes": 5,
            "is_active": True
        }
    }
    create_res = await client.post("/api/v1/wells", json=well_payload)
    assert create_res.status_code == 201
    assert create_res.json()["well_code"] == "WELL-API-01"

    # 2. Get well config
    cfg_res = await client.get("/api/v1/wells/WELL-API-01/config")
    assert cfg_res.status_code == 200
    assert cfg_res.json()["wc_threshold"] == 78.0

    # 3. Update well config
    update_res = await client.put("/api/v1/wells/WELL-API-01/config", json={"wc_threshold": 82.5})
    assert update_res.status_code == 200
    assert update_res.json()["wc_threshold"] == 82.5


@pytest.mark.asyncio
async def test_readings_and_dashboard_flow(client):
    now = datetime.now(timezone.utc).isoformat()
    # 1. Ingest reading
    reading_payload = {
        "well_code": "WELL-API-02",
        "timestamp": now,
        "oil_rate": 800.0,
        "water_rate": 200.0,
        "wc_value": 20.0,
        "wc_unit": "%",
        "source": "SOFTWARE_API"
    }
    post_res = await client.post("/api/v1/readings", json=reading_payload)
    assert post_res.status_code in {200, 201}

    # 2. Query dashboard
    dash_res = await client.get("/api/v1/dashboard?well_code=WELL-API-02")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["well_code"] == "WELL-API-02"
    assert len(dash_data["kpis"]) >= 3

    # Check Water Cut KPI
    wc_kpi = next(k for k in dash_data["kpis"] if k["metric_key"] == "water_cut")
    assert wc_kpi["value"] == 20.0
    assert wc_kpi["status"] == "NORMAL"


@pytest.mark.asyncio
async def test_dashboard_data_unavailable_state(client):
    # Ingest well reading with unavailable Water Cut
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "well_code": "WELL-API-UNAVAIL",
        "timestamp": now,
        "is_data_unavailable": True,
        "source": "SOFTWARE_API"
    }
    await client.post("/api/v1/readings", json=payload)

    dash_res = await client.get("/api/v1/dashboard?well_code=WELL-API-UNAVAIL")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    wc_kpi = next(k for k in dash_data["kpis"] if k["metric_key"] == "water_cut")
    assert wc_kpi["status"] == "DATA_UNAVAILABLE"
    assert wc_kpi["display_value"] == "DATA_UNAVAILABLE"
    assert wc_kpi["value"] is None


@pytest.mark.asyncio
async def test_well_crud_update_and_delete(client):
    # 1. Create a well
    create_payload = {
        "well_code": "WELL-CUSTOM-99",
        "field_name": "GHAWAR_SOUTH",
        "status": "ACTIVE",
        "config": {"wc_threshold": 75.0}
    }
    res = await client.post("/api/v1/wells", json=create_payload)
    assert res.status_code == 201

    # 2. Update well
    update_payload = {
        "field_name": "GHAWAR_NORTH",
        "status": "SHUT_IN",
        "wc_threshold": 65.0
    }
    update_res = await client.put("/api/v1/wells/WELL-CUSTOM-99", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["field_name"] == "GHAWAR_NORTH"
    assert update_res.json()["status"] == "SHUT_IN"

    # 3. Delete well
    del_res = await client.delete("/api/v1/wells/WELL-CUSTOM-99")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"

    # 4. Verify 404
    get_res = await client.get("/api/v1/wells/WELL-CUSTOM-99")
    assert get_res.status_code == 404

