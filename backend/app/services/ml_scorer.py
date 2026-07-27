"""
Phase 5: ML-based risk scorer.

Trains a logistic regression and random forest on file-level SonarQube metrics
(+ churn), labelled by the rule-based scorer. Both experiments are tracked in
MLflow so you can compare them against the rule-based baseline.
"""
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
import pandas as pd
from app.config import settings

# File-level ceilings — much tighter than repo-level ceilings in risk_scorer.py
# (a single file with 3 vulns is critical; at repo level 3/20 was nearly nothing)
_FILE_CEILINGS = {
    "bugs": 5,
    "vulnerabilities": 3,
    "code_smells": 20,
    "cognitive_complexity": 50,
    "duplicated_lines_density": 30,
    "severity_score": 10,   # weighted severity sum ceiling
}
_FILE_WEIGHTS = {
    "bugs": 0.20,
    "vulnerabilities": 0.15,
    "code_smells": 0.12,
    "cognitive_complexity": 0.13,
    "duplicated_lines_density": 0.08,
    "sqale_rating": 0.12,
    "severity_score": 0.20,  # severity-weighted violations get significant weight
}

# BLOCKER=5, CRITICAL=4, MAJOR=3, MINOR=2, INFO=1
_SEVERITY_WEIGHTS = {
    "blocker_violations": 5,
    "critical_violations": 4,
    "major_violations": 3,
    "minor_violations": 2,
    "info_violations": 1,
}


def _compute_severity_score(metrics: dict) -> float:
    """Weighted sum of violations by severity, normalised to 0–1."""
    def safe(key):
        try:
            return float(metrics.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0
    raw = sum(safe(k) * w for k, w in _SEVERITY_WEIGHTS.items())
    return min(raw / _FILE_CEILINGS["severity_score"], 1.0)


def compute_file_risk_score(metrics: dict) -> float:
    """0–100 risk score using file-appropriate ceilings with severity weighting."""
    def safe(key):
        try:
            return float(metrics.get(key, 0) or 0)
        except (ValueError, TypeError):
            return 0.0

    components = {k: min(safe(k) / ceil, 1.0) for k, ceil in _FILE_CEILINGS.items() if k != "severity_score"}
    components["sqale_rating"] = (safe("sqale_rating") - 1) / 4  # 1–5 → 0–1
    components["severity_score"] = _compute_severity_score(metrics)

    raw = sum(_FILE_WEIGHTS[k] * v for k, v in components.items())
    return round(raw * 100, 1)


HIGH_RISK_THRESHOLD = 20

FEATURE_COLS = [
    "bugs", "vulnerabilities", "code_smells",
    "cognitive_complexity", "duplicated_lines_density",
    "sqale_rating", "churn", "severity_score",
]


def _components_to_df(components: list[dict], churn_map: dict[str, int]) -> pd.DataFrame:
    rows = []
    for c in components:
        m = c["metrics"]

        def safe(key, default=0.0):
            try:
                return float(m.get(key, default) or default)
            except (ValueError, TypeError):
                return default

        path = c["key"].split(":", 1)[-1]
        file_score = compute_file_risk_score(m)

        rows.append({
            "key": c["key"],
            "bugs": safe("bugs"),
            "vulnerabilities": safe("vulnerabilities"),
            "code_smells": safe("code_smells"),
            "cognitive_complexity": safe("cognitive_complexity"),
            "duplicated_lines_density": safe("duplicated_lines_density"),
            "sqale_rating": safe("sqale_rating", 1.0),
            "churn": float(churn_map.get(path, 0)),
            "severity_score": _compute_severity_score(m),
            "rule_based_score": file_score,
            "label": 1 if file_score >= HIGH_RISK_THRESHOLD else 0,
        })
    return pd.DataFrame(rows)


def _eval_metrics(y_true, y_pred, y_proba) -> dict:
    cm = confusion_matrix(y_true, y_pred).tolist()
    metrics = {
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
        "confusion_matrix": cm,
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)

        def _safe_float(v):
            f = float(v)
            if np.isnan(f) or np.isinf(f):
                return None
            return round(f, 4)

        metrics["roc_curve"] = {
            "fpr": [_safe_float(v) for v in fpr],
            "tpr": [_safe_float(v) for v in tpr],
            "thresholds": [_safe_float(v) for v in thresholds],
        }
    else:
        metrics["roc_auc"] = None
        metrics["roc_curve"] = None
    return metrics


def _train_and_log(
    model_name: str,
    clf,
    X: np.ndarray,
    y: np.ndarray,
    project_key: str,
    n_samples: int,
    n_high_risk: int,
) -> dict:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("ml-risk-scoring")

    with mlflow.start_run(run_name=f"{model_name}-{project_key}") as run:
        mlflow.log_params({
            "project": project_key,
            "model": model_name,
            "n_samples": n_samples,
            "n_high_risk": n_high_risk,
            "high_risk_threshold": HIGH_RISK_THRESHOLD,
            "features": ",".join(FEATURE_COLS),
        })

        n_classes = len(np.unique(y))
        if n_classes < 2:
            # Only one class present — log a dummy model and return null metrics
            dummy = DummyClassifier(strategy="most_frequent").fit(X, y)
            mlflow.sklearn.log_model(dummy, artifact_path=model_name)
            metrics = {
                "precision": None, "recall": None, "f1": None,
                "roc_auc": None, "roc_curve": None,
                "confusion_matrix": [[int(y.sum()), 0], [0, 0]],
                "note": f"Only class 0 present at threshold={HIGH_RISK_THRESHOLD}. All files are low-risk. Consider lowering the threshold.",
                "run_id": run.info.run_id,
                "model_name": model_name,
            }
            mlflow.log_metrics({"n_high_risk_detected": 0, "roc_auc": 0.0})
            return metrics

        # Stratified CV ensures each fold has both classes
        n_splits = min(5, n_high_risk, n_samples - n_high_risk)
        n_splits = max(2, n_splits)
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        y_pred = cross_val_predict(clf, X, y, cv=cv, method="predict")
        y_proba = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]

        metrics = _eval_metrics(y, y_pred, y_proba)

        mlflow.log_metrics({
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "roc_auc": metrics.get("roc_auc") or 0.0,
            "n_high_risk_detected": int(y_pred.sum()),
        })

        # Fit on full dataset and log model
        clf.fit(X, y)
        mlflow.sklearn.log_model(clf, artifact_path=model_name)

        # Log feature importances for random forest
        if hasattr(clf, "steps"):
            final_estimator = clf.steps[-1][1]
        else:
            final_estimator = clf

        if hasattr(final_estimator, "feature_importances_"):
            importances = dict(zip(FEATURE_COLS, [
                round(float(v), 4) for v in final_estimator.feature_importances_
            ]))
            mlflow.log_dict(importances, "feature_importances.json")
            metrics["feature_importances"] = importances

        metrics["run_id"] = run.info.run_id
        metrics["model_name"] = model_name
        return metrics


def train(components: list[dict], churn_map: dict[str, int], project_key: str) -> dict:
    """Train both models and return evaluation results."""
    df = _components_to_df(components, churn_map)

    if len(df) < 4:
        return {"error": "Not enough file-level data to train (need ≥ 4 files).", "n_samples": len(df)}

    X = df[FEATURE_COLS].values
    y = df["label"].values

    n_high_risk = int(y.sum())
    n_low_risk = len(df) - n_high_risk

    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)

    lr_metrics = _train_and_log("logistic-regression", lr_pipe, X, y, project_key, len(df), n_high_risk)
    rf_metrics = _train_and_log("random-forest", rf, X, y, project_key, len(df), n_high_risk)

    return {
        "n_samples": len(df),
        "n_high_risk": n_high_risk,
        "n_low_risk": n_low_risk,
        "models": {
            "logistic_regression": lr_metrics,
            "random_forest": rf_metrics,
        },
        "files": df[["key", "rule_based_score", "label"]].to_dict(orient="records"),
    }


def predict(components: list[dict], churn_map: dict[str, int]) -> list[dict]:
    """
    Score each file using both models (trained inline on the same data).
    Returns per-file predictions alongside rule-based scores.
    """
    df = _components_to_df(components, churn_map)
    if len(df) < 4:
        return []

    X = df[FEATURE_COLS].values
    y = df["label"].values

    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    rf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)

    n_classes = len(np.unique(y))
    if n_classes < 2:
        lr_proba = np.zeros(len(X))
        rf_proba = np.zeros(len(X))
    else:
        lr_pipe.fit(X, y)
        rf.fit(X, y)
        lr_proba = lr_pipe.predict_proba(X)[:, 1]
        rf_proba = rf.predict_proba(X)[:, 1]

    results = []
    for i, row in df.iterrows():
        results.append({
            "key": row["key"],
            "rule_based_score": round(row["rule_based_score"], 1),
            "lr_risk_proba": round(float(lr_proba[i]), 4),
            "rf_risk_proba": round(float(rf_proba[i]), 4),
            "label": int(row["label"]),
            "churn": int(row["churn"]),
            "bugs": int(row["bugs"]),
            "vulnerabilities": int(row["vulnerabilities"]),
            "code_smells": int(row["code_smells"]),
            "severity_score": round(float(row["severity_score"]), 3),
        })

    results.sort(key=lambda x: (x["lr_risk_proba"] + x["rf_risk_proba"]), reverse=True)
    return results
