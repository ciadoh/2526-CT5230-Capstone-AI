import threading
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.state import get_active_repo

router = APIRouter(prefix="/api/scan", tags=["scan"])

_status: dict = {"running": False, "last": None}


def _run_scanner(repo: str):
    try:
        import docker
        client = docker.from_env()
        client.containers.run(
            "capstone_ai-scanner",
            environment={
                "TARGET_REPO": repo,
                "SONAR_TOKEN": settings.sonarqube_token,
                "SONAR_HOST_URL": "http://sonarqube:9000",
                "GITHUB_TOKEN": settings.github_token,
            },
            volumes={"/tmp/ca-bundle.pem": {"bind": "/tmp/ca-bundle.pem", "mode": "ro"}},
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
