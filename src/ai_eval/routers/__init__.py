"""Router package — aggregates all route modules."""

from fastapi import APIRouter

from ai_eval.routers.configs import router as configs_router
from ai_eval.routers.containers import router as containers_router
from ai_eval.routers.dashboard import router as dashboard_router
from ai_eval.routers.datasets import router as datasets_router
from ai_eval.routers.generate_schema import router as generate_schema_router
from ai_eval.routers.playground import router as playground_router
from ai_eval.routers.runs import router as runs_router
from ai_eval.routers.vector_stores import router as vector_stores_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(configs_router)
router.include_router(datasets_router)
router.include_router(vector_stores_router)
router.include_router(containers_router)
router.include_router(runs_router)
router.include_router(playground_router)
router.include_router(generate_schema_router)
