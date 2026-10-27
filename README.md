# SMART GUARDIAN

### Digital Oilfield & Petroleum Reservoir Intelligence Platform (Phase 1)

**Smart Guardian** is a production-grade digital oilfield and reservoir-engineering intelligence platform engineered to transform real field data into:
- Real-time production surveillance
- Early warning detection
- Reservoir-engineering analysis
- Evidence-based diagnostics
- Engineering decision support
- Production and reservoir performance intelligence

---

## 1. Safety Rule & Operational Boundary

> [!CAUTION]
> **READ-ONLY INDUSTRIAL BOUNDARY (STRICTLY ENFORCED)**
> In Phase 1, Smart Guardian **MUST NOT** send control commands to field equipment.
> The integration with Control Room systems, SCADA/Historian, and field instruments is strictly:
> `CONTROL ROOM / FIELD SYSTEM` $\rightarrow$ `READ ONLY` $\rightarrow$ `SMART GUARDIAN`
> 
> Absolutely **NO**:
> - Valve control or actuation
> - Pump control
> - Choke adjustment
> - Injection control
> - Well shutdown / ESD commands
> - Autonomous field control
> 
> Smart Guardian is a decision-support and surveillance intelligence system, not an autonomous control system.

---

## 2. Core Engineering Principles

The platform follows this conceptual pipeline:
$$\text{Real Field Data} \rightarrow \text{Data Ingestion} \rightarrow \text{Validation / Quality} \rightarrow \text{Canonical Data Model} \rightarrow \text{Production Surveillance} \rightarrow \text{Reservoir Engines} \rightarrow \text{Evidence} \rightarrow \text{Diagnostics} \rightarrow \text{Early Warning} \rightarrow \text{Decision Support}$$

### Phase 1 Scope & Boundary
1. **Scope Limit**: Phase 1 implements the platform foundation, robust data ingestion, validation, data quality tracking, time-series storage, basic production surveillance, and Water Cut early warning.
2. **Phase 1 Restriction**: Advanced reservoir physics equations (Chan diagnostics, Havlena–Odeh Material Balance, Buckley–Leverett fractional flow, coning/channeling physics) are strictly reserved for Phase 2.
3. **No Root-Cause Assumption**: A Water Cut threshold exceedance triggers `WATER_CUT_THRESHOLD_EXCEEDED` warning. The system **never** claims an unverified reservoir root cause (e.g. Channeling, Coning, Fracture, Cement Failure) based solely on Water Cut without multi-evidence diagnostic engines.
4. **Data Integrity Principle**: If an engineering measurement is unavailable from a field source, the platform records and displays `DATA_UNAVAILABLE`. It **never** silently replaces missing values with $0$, arbitrary defaults, or hidden fallbacks. Missing Water Cut never becomes $\text{WC} = 0$.
5. **Decoupled Architecture**: Frontend displays backend results. All engineering calculations, validation, and surveillance logic reside strictly in the backend.

---

## 3. Technology Stack

### Backend
- **Language & Runtime**: Python 3.12+
- **API Framework**: FastAPI (Async REST API)
- **Database**: PostgreSQL 16 with TimescaleDB extension (Hypertables partitioned by `timestamp`)
- **ORM & Migrations**: SQLAlchemy 2.0 + Alembic migrations
- **Validation**: Pydantic v2
- **Testing**: Pytest, Pytest-asyncio, HTTPX

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Server State / Cache**: TanStack Query (30-second polling interval)
- **Internationalization**: Full English (LTR) and Arabic (RTL) localization with native petroleum engineering terminology.

---

## 4. Architecture & Service Structure

```
smart-guardian/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Environment & threshold configuration
│   │   │   ├── logging.py            # Structured JSON audit logging
│   │   │   ├── security.py           # Read-only barrier enforcement
│   │   │   └── rate_limiter.py       # Infrastructure rate limiting per source & well
│   │   ├── database/
│   │   │   ├── session.py            # Async engine & session lifecycle
│   │   │   └── base.py               # Declarative model metadata
│   │   ├── models/
│   │   │   ├── well.py               # Well master table
│   │   │   ├── well_config.py        # Per-well operational thresholds
│   │   │   ├── readings.py           # Production readings (TimescaleDB hypertable)
│   │   │   ├── separator.py          # Separator telemetry (TimescaleDB hypertable)
│   │   │   ├── manual.py             # Manual operator readings & audit trail
│   │   │   ├── alert.py              # Structured alerts & lifecycle
│   │   │   └── analysis.py           # Surveillance analysis results
│   │   ├── schemas/                  # Pydantic v2 request/response contracts
│   │   ├── services/
│   │   │   ├── validation.py         # Petroleum data validation & normalization
│   │   │   ├── idempotency.py        # SHA-256 deduplication & retry safety
│   │   │   ├── ingestion.py          # Orchestrated ingestion pipeline
│   │   │   ├── surveillance.py       # Water cut surveillance engine
│   │   │   ├── alert_service.py      # Duplicate prevention & cooldown lifecycle
│   │   │   ├── dashboard_service.py  # Dashboard summary assembler
│   │   │   └── analysis_future_stubs.py # Extensibility contracts for Phase 2
│   │   ├── routers/                  # Clean REST API endpoints
│   │   └── main.py                   # FastAPI application entrypoint
│   ├── migrations/                   # Alembic migration scripts
│   ├── tests/                        # Comprehensive test suite (26 tests)
│   ├── verify_e2e.py                 # 13-step end-to-end architectural verification
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                      # App router layout & homepage
│   │   ├── components/               # Header, KpiCard, AlertList, Ingestion modals
│   │   ├── context/                  # LanguageContext (RTL/LTR) & WellContext
│   │   ├── locales/                  # en.json and ar.json translation dictionaries
│   │   ├── lib/                      # API client & formatting utilities
│   │   └── types/                    # TypeScript data contracts
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docker-compose.yml                # TimescaleDB + Backend + Frontend stack
└── README.md
```

---

## 5. Running the Application

### Option A: Using Docker Compose (Full Stack with TimescaleDB)

```bash
# Start TimescaleDB, Backend, and Frontend
docker compose up -d

# Run Alembic migrations inside container
docker compose exec backend alembic upgrade head
```

- **Surveillance Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **TimescaleDB Port**: `localhost:5432`

---

### Option B: Local Development

#### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations (PostgreSQL/TimescaleDB or local SQLite)
cd backend
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

---

## 6. Running Tests & Verification

### Run Automated Backend Unit & Integration Tests (26 Tests)
```bash
pytest backend/tests -v
```

### Run End-to-End Architectural Verification
```bash
python backend/verify_e2e.py
```

### Run Frontend Production Build
```bash
cd frontend
npm run build
```
