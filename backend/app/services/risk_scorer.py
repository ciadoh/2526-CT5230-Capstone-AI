"""
Rule-based risk scorer (Phase 4) and a simple ML risk model (Phase 5).
MLflow tracks all experiments.
"""
import mlflow
import numpy as np
from app.config import settings


def _flatten_metrics(measures: list[dict]) -> dict:
    return {m["metric"]: m.get("value", "0") for m in measures}


def compute_risk_score(measures: list[dict]) -> dict:
    """Weighted rule-based scoring — higher = more debt risk (0–100)."""
    m = _flatten_metrics(measures)

    def safe_float(key: float, default: float = 0.0) -> float:
        try:
            return float(m.get(key, default))
        except (ValueError, TypeError):
            return default

    # Rating letters map to 1-5 (A=1 best, E=5 worst)
    rating_map = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

    weights = {
        "bugs": 0.25,
        "vulnerabilities": 0.20,
        "code_smells": 0.15,
        "cognitive_complexity": 0.15,
        "duplicated_lines_density": 0.10,
        "sqale_rating": 0.15,
    }

    bugs = min(safe_float("bugs") / 50, 1.0)
    vulns = min(safe_float("vulnerabilities") / 20, 1.0)
    smells = min(safe_float("code_smells") / 500, 1.0)
    complexity = min(safe_float("cognitive_complexity") / 1000, 1.0)
    duplication = min(safe_float("duplicated_lines_density") / 30, 1.0)
    # sqale_rating is 1.0 (A) – 5.0 (E); normalise to 0–1
    maint = (safe_float("sqale_rating") - 1) / 4

    raw = (
        weights["bugs"] * bugs
        + weights["vulnerabilities"] * vulns
        + weights["code_smells"] * smells
        + weights["cognitive_complexity"] * complexity
        + weights["duplicated_lines_density"] * duplication
        + weights["sqale_rating"] * maint
    )

    score = round(raw * 100, 1)

    category = "LOW"
    if score >= 60:
        category = "CRITICAL"
    elif score >= 40:
        category = "HIGH"
    elif score >= 20:
        category = "MEDIUM"

    return {
        "score": score,
        "category": category,
        "breakdown": {
            "bugs": round(bugs * weights["bugs"] * 100, 1),
            "vulnerabilities": round(vulns * weights["vulnerabilities"] * 100, 1),
            "code_smells": round(smells * weights["code_smells"] * 100, 1),
            "complexity": round(complexity * weights["cognitive_complexity"] * 100, 1),
            "duplication": round(duplication * weights["duplicated_lines_density"] * 100, 1),
            "maintainability": round(maint * weights["sqale_rating"] * 100, 1),
        },
    }


def log_to_mlflow(project_key: str, measures: list[dict], risk: dict) -> str:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("technical-debt-scoring")

    m = _flatten_metrics(measures)

    with mlflow.start_run(run_name=f"risk-score-{project_key}") as run:
        mlflow.log_params({"project": project_key, "scorer": "rule-based-v1"})
        mlflow.log_metrics(
            {
                "risk_score": risk["score"],
                "bugs": float(m.get("bugs", 0)),
                "vulnerabilities": float(m.get("vulnerabilities", 0)),
                "code_smells": float(m.get("code_smells", 0)),
                "duplicated_lines_density": float(m.get("duplicated_lines_density", 0) or 0),
                "technical_debt_minutes": float(m.get("sqale_index", 0) or 0),
            }
        )
        mlflow.log_dict(risk, "risk_breakdown.json")
        return run.info.run_id
