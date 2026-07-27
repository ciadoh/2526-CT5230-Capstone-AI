from fastapi import APIRouter
from app.services import sonar_client, github_client
from app.services.risk_scorer import compute_risk_score, log_to_mlflow
from app.state import get_active_repo
from typing import Optional

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary():
    owner, repo = get_active_repo().split("/", 1)
    project_key = get_active_repo().replace("/", "-")

    gh_repo, gh_languages = await _gather_github(owner, repo)

    try:
        sonar_metrics = await sonar_client.get_metrics(project_key)
        measures = sonar_metrics.get("component", {}).get("measures", [])
        risk = compute_risk_score(measures)
        run_id = log_to_mlflow(project_key, measures, risk)
        metrics_flat = {m["metric"]: m.get("value") for m in measures}
    except Exception:
        measures, risk, metrics_flat, run_id = [], {"score": None, "category": "UNAVAILABLE", "breakdown": {}}, {}, None

    return {
        "repo": {
            "full_name": gh_repo.get("full_name"),
            "description": gh_repo.get("description"),
            "stars": gh_repo.get("stargazers_count"),
            "forks": gh_repo.get("forks_count"),
            "open_issues": gh_repo.get("open_issues_count"),
            "default_branch": gh_repo.get("default_branch"),
            "languages": gh_languages,
        },
        "risk": risk,
        "metrics": metrics_flat,
        "mlflow_run_id": run_id,
    }


@router.get("/churn")
async def get_churn():
    """Commit count per file — top files by churn, cross-referenced with SonarQube components."""
    owner, repo = get_active_repo().split("/", 1)
    project_key = get_active_repo().replace("/", "-")

    try:
        components = await sonar_client.get_component_tree(project_key)
    except Exception:
        return {"churn": [], "error": "SonarQube unavailable"}

    # SonarQube component keys look like "project-key:path/to/File.js"
    file_paths = [c["key"].split(":", 1)[-1] for c in components]
    churn_map = await github_client.get_file_churn(owner, repo, file_paths)

    result = []
    for c in components:
        path = c["key"].split(":", 1)[-1]
        result.append({
            "key": c["key"],
            "name": c["name"],
            "path": path,
            "churn": churn_map.get(path, 0),
            "metrics": c["metrics"],
        })

    result.sort(key=lambda x: x["churn"], reverse=True)
    return {"churn": result}


async def _gather_github(owner: str, repo: str):
    import asyncio
    return await asyncio.gather(
        github_client.get_repo(owner, repo),
        github_client.get_languages(owner, repo),
    )
