import threading
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.state import get_active_repo

router = APIRouter(prefix="/api/scan", tags=["scan"])

_status: dict = {"running": False, "last": None}


SCANNER_IMAGE = "capstone_ai-scanner:latest"


def _run_scanner(repo: str):
    try:
        import docker
        client = docker.from_env()
        try:
            client.images.get(SCANNER_IMAGE)
        except docker.errors.ImageNotFound:
            client.images.build(path="/scanner-build", tag=SCANNER_IMAGE, rm=True)
        client.containers.run(
            SCANNER_IMAGE,
            environment={
                "TARGET_REPO": repo,
                "SONAR_TOKEN": settings.sonarqube_token,
                "SONAR_HOST_URL": "http://sonarqube:9000",
                "GITHUB_TOKEN": settings.github_token,
            },
            network="capstone_ai_default",
            remove=True,
            detach=False,
        )
        _status["last"] = {"success": True, "repo": repo}
    except Exception as e:
        _status["last"] = {"success": False, "error": str(e), "repo": repo}
    finally:
        _status["running"] = False


@router.post("/trigger")
async def trigger_scan():
    if _status["running"]:
        raise HTTPException(status_code=409, detail="Scan already in progress")
    repo = get_active_repo()
    _status["running"] = True
    _status["last"] = None
    threading.Thread(target=_run_scanner, args=(repo,), daemon=True).start()
    return {"status": "started", "repo": repo}


@router.get("/status")
async def scan_status():
    return {"running": _status["running"], "last": _status["last"]}
