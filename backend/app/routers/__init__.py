from app.routers.wells import router as wells_router
from app.routers.readings import router as readings_router
from app.routers.separator import router as separator_router
from app.routers.alerts import router as alerts_router
from app.routers.analysis import router as analysis_router
from app.routers.dashboard import router as dashboard_router
from app.routers.reservoir import router as reservoir_router

__all__ = [
    "wells_router",
    "readings_router",
    "separator_router",
    "alerts_router",
    "analysis_router",
    "dashboard_router",
    "reservoir_router"
]
