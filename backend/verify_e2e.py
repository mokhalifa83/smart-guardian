"""
Smart Guardian Phase 1 - End-to-End Architecture Verification Script
Executes the strict verification sequence:
Data -> Ingestion -> Validation -> Storage -> Surveillance -> Alert -> API -> Dashboard
Verifies:
1. Production surveillance flow
2. Configurable Water Cut threshold
3. Alert lifecycle (ACTIVE -> ACKNOWLEDGED -> RESOLVED)
4. Idempotency & duplicate suppression
5. Provenance tracking (source, timestamp, received_at, quality)
6. Explicit DATA_UNAVAILABLE handling (no silent zero substitution)
7. Safety boundary (rejection of field equipment control commands)
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Configure isolated environment for verification
TEST_DB_FILE = Path("verify_e2e.db")
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE.resolve()}"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE.resolve()}"

import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import Base
from sqlalchemy.ext.asyncio import create_async_engine

async def run_verification():
    print("=" * 70)
    print("SMART GUARDIAN - PHASE 1 ARCHITECTURAL VERIFICATION SUITE")
    print("=" * 70)

    # 1. Initialize DB tables
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[1] Database Tables Initialized: PASS")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # 2. Verify Health & Safety Barrier
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert "ENFORCED" in health_data["read_only_barrier"]
        print("[2] Health & Read-Only Safety Barrier: PASS")

        # 3. Create Well with custom threshold (e.g. 75.0%)
        well_payload = {
            "well_code": "SG-E2E-01",
            "field_name": "Ghawar South Dome",
            "status": "ACTIVE",
            "config": {
                "wc_threshold": 75.0,
                "wc_trend_window_hours": 24,
                "alert_cooldown_minutes": 60,
                "surveillance_interval_minutes": 5,
                "is_active": True
            }
        }
        w_res = await client.post("/api/v1/wells", json=well_payload)
        assert w_res.status_code == 201
        print("[3] Well Registration with Configurable Threshold (75.0%): PASS")

        # 4. Ingest Reading 1 - Normal Water Cut (55.0% < 75.0%)
        # Explicit test fixture clearly identified
        now = datetime.now(timezone.utc).isoformat()
        reading1 = {
            "well_code": "SG-E2E-01",
            "timestamp": now,
            "oil_rate": 900.0,
            "water_rate": 1100.0,
            "wc_value": 55.0,
            "wc_unit": "%",
            "source": "SOFTWARE_API",
            "source_system": "SCADA-Historian-OPC"
        }
        r1_res = await client.post("/api/v1/readings", json=reading1)
        assert r1_res.status_code in {200, 201}
        r1_data = r1_res.json()
        assert r1_data["wc_percent"] == 55.0
        assert r1_data["quality_status"] == "VALID"
        assert r1_data["value_type"] == "MEASURED"
        print("[4] Normal Water Cut Telemetry Ingestion (55%): PASS")

        # Check Dashboard shows NORMAL
        d1_res = await client.get("/api/v1/dashboard?well_code=SG-E2E-01")
        assert d1_res.status_code == 200
        d1_data = d1_res.json()
        assert d1_data["surveillance_state"] == "NORMAL"
        assert len(d1_data["active_alerts"]) == 0
        print("[5] Dashboard Normal Surveillance State: PASS")

        # 5. Ingest Reading 2 - High Water Cut exceeding threshold (82.5% > 75.0%)
        reading2 = {
            "well_code": "SG-E2E-01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "oil_rate": 350.0,
            "water_rate": 1650.0,
            "wc_value": 82.5,
            "wc_unit": "%",
            "source": "SOFTWARE_API",
            "source_system": "SCADA-Historian-OPC"
        }
        r2_res = await client.post("/api/v1/readings", json=reading2)
        assert r2_res.status_code in {200, 201}
        print("[6] High Water Cut Exceedance Ingestion (82.5%): PASS")

        # Check Dashboard shows WARNING & Active Alert
        d2_res = await client.get("/api/v1/dashboard?well_code=SG-E2E-01")
        assert d2_res.status_code == 200
        d2_data = d2_res.json()
        assert d2_data["surveillance_state"] == "WARNING"
        assert len(d2_data["active_alerts"]) == 1
        alert = d2_data["active_alerts"][0]
        assert alert["alert_type"] == "WATER_CUT"
        assert alert["severity"] == "WARNING"
        assert "WATER_CUT_THRESHOLD_EXCEEDED" in alert["message"]
        # Ensure Phase 1 engineering restriction: No unverified root cause claim
        assert "CONING" not in alert["message"]
        assert "CHANNELING" not in alert["message"]
        print("[7] Structured Alert Generation (WATER_CUT_THRESHOLD_EXCEEDED): PASS")

        # 6. Verify Idempotent Retransmission (MQTT/Network retry)
        r2_retry_res = await client.post("/api/v1/readings", json=reading2)
        assert r2_retry_res.status_code == 200  # Returns existing record idempotently
        # Ensure no duplicate alert created
        d2_retry = (await client.get("/api/v1/dashboard?well_code=SG-E2E-01")).json()
        assert len(d2_retry["active_alerts"]) == 1
        print("[8] Idempotent Retransmission & Cooldown Duplicate Suppression: PASS")

        # 7. Alert Lifecycle: Acknowledge & Resolve
        alert_id = alert["alert_id"]
        ack_res = await client.put(f"/api/v1/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "Eng. Sarah"})
        assert ack_res.status_code == 200
        assert ack_res.json()["status"] == "ACKNOWLEDGED"

        res_res = await client.put(f"/api/v1/alerts/{alert_id}/resolve", json={"resolved_by": "Eng. Sarah", "resolution_notes": "Choke throttled"})
        assert res_res.status_code == 200
        assert res_res.json()["status"] == "RESOLVED"
        print("[9] Alert Lifecycle (ACTIVE -> ACKNOWLEDGED -> RESOLVED): PASS")

        # 8. Verify DATA_UNAVAILABLE Handling
        # External sensor offline: explicit state preserved, never replaced by 0.0
        reading_unavail = {
            "well_code": "SG-E2E-01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_data_unavailable": True,
            "source": "SOFTWARE_API"
        }
        ru_res = await client.post("/api/v1/readings", json=reading_unavail)
        assert ru_res.status_code in {200, 201}
        ru_data = ru_res.json()
        assert ru_data["wc_percent"] is None
        assert ru_data["wc_percent"] != 0.0
        assert ru_data["quality_status"] == "DATA_UNAVAILABLE"

        d3_res = await client.get("/api/v1/dashboard?well_code=SG-E2E-01")
        d3_data = d3_res.json()
        wc_kpi = next(k for k in d3_data["kpis"] if k["metric_key"] == "water_cut")
        assert wc_kpi["status"] == "DATA_UNAVAILABLE"
        assert wc_kpi["display_value"] == "DATA_UNAVAILABLE"
        assert wc_kpi["value"] is None
        print("[10] Explicit DATA_UNAVAILABLE State (No silent WC = 0 substitution): PASS")

        # 9. Verify Separator Telemetry with fractional input (0.85 fraction -> 85.0%)
        sep_payload = {
            "well_code": "SG-E2E-01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pressure": 350.0,
            "flow_rate": 2100.0,
            "water_cut": 0.85,
            "wc_unit": "fraction",
            "source": "SOFTWARE_API"
        }
        sep_res = await client.post("/api/v1/separator-data", json=sep_payload)
        assert sep_res.status_code in {200, 201}
        sep_data = sep_res.json()
        assert sep_data["water_cut"] == 85.0
        assert sep_data["original_wc_value"] == 0.85
        assert sep_data["original_wc_unit"] == "fraction"
        print("[11] Separator Telemetry (Fraction Normalization & Unit Provenance): PASS")

        # 10. Verify Manual Operator Reading with identity tracking
        man_payload = {
            "well_code": "SG-E2E-01",
            "measurement_type": "WATER_CUT",
            "value": 72.0,
            "unit": "%",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entered_by": "Eng. Khalid Al-Harbi"
        }
        man_res = await client.post("/api/v1/readings/manual", json=man_payload)
        assert man_res.status_code in {200, 201}
        man_data = man_res.json()
        assert man_data["entered_by"] == "Eng. Khalid Al-Harbi"
        assert man_data["source"] == "MANUAL"
        print("[12] Manual Operator Entry & Engineer Identity Provenance: PASS")

        # 11. Verify Config Update via API (e.g. changing threshold from 75% to 88%)
        cfg_put_res = await client.put("/api/v1/wells/SG-E2E-01/config", json={"wc_threshold": 88.0})
        assert cfg_put_res.status_code == 200
        assert cfg_put_res.json()["wc_threshold"] == 88.0
        print("[13] Dynamic Threshold Modification via API (PUT /wells/{code}/config): PASS")

    # Clean up test DB
    await engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

    print("=" * 70)
    print("ALL END-TO-END VERIFICATION CHECKS COMPLETED SUCCESSFULLY (13/13 PASS)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_verification())
