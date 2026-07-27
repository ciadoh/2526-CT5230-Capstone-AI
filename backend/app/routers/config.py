from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.state import get_active_repo, set_active_repo, AVAILABLE_REPOS, PR_ENABLED_REPOS

router = APIRouter(prefix="/api/config", tags=["config"])


class RepoSwitch(BaseModel):
    repo: str


@router.get("/repo")
async def get_repo():
    repo = get_active_repo()
    return {"active_repo": repo, "available_repos": AVAILABLE_REPOS, "pr_enabled": repo in PR_ENABLED_REPOS}


@router.post("/repo")
async def switch_repo(body: RepoSwitch):
    if body.repo not in AVAILABLE_REPOS:
        raise HTTPException(status_code=400, detail=f"Unknown repo: {body.repo}")
    set_active_repo(body.repo)
    return {"active_repo": body.repo, "pr_enabled": body.repo in PR_ENABLED_REPOS}
