from fastapi import APIRouter, HTTPException
from app.services import sonar_client, github_client
from app.services import ml_scorer
from app.state import get_active_repo

router = APIRouter(prefix="/api/ml", tags=["ml"])


async def _fetch_data(project_key: str, owner: str, repo: str):
    try:
        components = await sonar_client.get_component_tree(project_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SonarQube unavailable: {e}")

    if not components:
        raise HTTPException(status_code=404, detail="No file-level SonarQube data found. Run a scan first.")

    file_paths = [c["key"].split(":", 1)[-1] for c in components]
    churn_map = await github_client.get_file_churn(owner, repo, file_paths)
    return components, churn_map


@router.post("/train")
async def train_models():
    """
    Train logistic regression and random forest on file-level metrics.
    Logs both experiments to MLflow and returns evaluation metrics.
    """
    owner, repo = get_active_repo().split("/", 1)
    project_key = get_active_repo().replace("/", "-")
    components, churn_map = await _fetch_data(project_key, owner, repo)
    result = ml_scorer.train(components, churn_map, project_key)
    return result


@router.get("/predict")
async def predict_risk():
    """
    Return per-file risk scores from both ML models alongside rule-based scores.
    Useful for the frontend heatmap and for comparing model outputs.
    """
    owner, repo = get_active_repo().split("/", 1)
    project_key = get_active_repo().replace("/", "-")
    components, churn_map = await _fetch_data(project_key, owner, repo)
    predictions = ml_scorer.predict(components, churn_map)
    return {"predictions": predictions, "n_files": len(predictions)}
