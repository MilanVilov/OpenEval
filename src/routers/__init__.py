"""Router package — aggregates all route modules."""

from fastapi import APIRouter

from src.routers.configs import router as configs_router
from src.routers.containers import router as containers_router
from src.routers.data_sources import router as data_sources_router
from src.routers.dashboard import router as dashboard_router
from src.routers.datasets import router as datasets_router
from src.routers.generate_schema import router as generate_schema_router
from src.routers.playground import router as playground_router
from src.routers.runs import router as runs_router
from src.routers.schedules import router as schedules_router
from src.routers.vector_stores import router as vector_stores_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(configs_router)
router.include_router(data_sources_router)
router.include_router(datasets_router)
router.include_router(vector_stores_router)
router.include_router(containers_router)
router.include_router(runs_router)
router.include_router(schedules_router)
router.include_router(playground_router)
router.include_router(generate_schema_router)
