from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.database.session import async_engine, Base
from app.routers import (
    wells_router,
    readings_router,
    separator_router,
    alerts_router,
    analysis_router,
    dashboard_router,
    reservoir_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT != "test":
        logger.info("Initializing Smart Guardian database schema...")
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Smart Guardian database initialized.")
        except Exception as e:
            logger.warning(f"Database initialization deferred or skipped: {e}")
    yield
    if settings.ENVIRONMENT != "test":
        try:
            await async_engine.dispose()
        except Exception:
            pass
        logger.info("Smart Guardian backend shutdown.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Smart Guardian: Production-grade digital oilfield and reservoir-engineering intelligence platform. "
        "Transforms real field data into real-time surveillance, early warning, and engineering decision support."
    ),
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled API Exception: {exc}",
        exc_info=True,
        extra={"structured_data": {"path": request.url.path, "method": request.method}}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred processing your request.",
            "path": request.url.path
        }
    )


# Health & Safety Barrier Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Smart Guardian Intelligence Platform",
        "version": settings.VERSION,
        "read_only_barrier": "ENFORCED (No field control commands permitted)"
    }


# Include v1 routers
api_prefix = settings.API_V1_STR
app.include_router(wells_router, prefix=api_prefix)
app.include_router(readings_router, prefix=api_prefix)
app.include_router(separator_router, prefix=api_prefix)
app.include_router(alerts_router, prefix=api_prefix)
app.include_router(analysis_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(reservoir_router, prefix=api_prefix)
