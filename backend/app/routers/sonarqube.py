from fastapi import APIRouter
from app.services import sonar_client
from app.state import get_active_repo

router = APIRouter(prefix="/api/sonar", tags=["sonarqube"])


def _project_key() -> str:
    return get_active_repo().replace("/", "-")


@router.get("/metrics")
async def get_metrics():
    return await sonar_client.get_metrics(_project_key())


@router.get("/issues")
async def get_issues(page_size: int = 50):
    return await sonar_client.get_issues(_project_key(), page_size)


@router.get("/hotspots")
async def get_hotspots():
    return await sonar_client.get_hotspots(_project_key())


@router.get("/history")
async def get_history(metric: str = "sqale_index"):
    return await sonar_client.get_history(_project_key(), metric)


@router.get("/components")
async def get_components():
    """Per-file metrics for all files in the project."""
    return await sonar_client.get_component_tree(_project_key())
