import os
import httpx
from fastapi import APIRouter
from app.config import settings

SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() != "false"

router = APIRouter(prefix="/api/mlflow", tags=["mlflow"])

MLFLOW_API = f"{settings.mlflow_tracking_uri}/api/2.0"


@router.get("/experiments")
async def list_experiments():
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.post(
            f"{MLFLOW_API}/mlflow/experiments/search",
            json={"max_results": 50},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


@router.get("/runs")
async def list_runs(
    experiment_name: str = "technical-debt-scoring",
    max_results: int = 10,
    page_token: str | None = None,
):
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.get(
            f"{MLFLOW_API}/mlflow/experiments/get-by-name",
            params={"experiment_name": experiment_name},
            timeout=10,
        )
        if r.status_code != 200:
            return {"runs": [], "next_page_token": None}
        exp_id = r.json()["experiment"]["experiment_id"]

        body: dict = {"experiment_ids": [exp_id], "max_results": max_results}
        if page_token:
            body["page_token"] = page_token

        r2 = await client.post(
            f"{MLFLOW_API}/mlflow/runs/search",
            json=body,
            timeout=10,
        )
        r2.raise_for_status()
        data = r2.json()
        return {
            "runs": data.get("runs", []),
            "next_page_token": data.get("next_page_token"),
        }
