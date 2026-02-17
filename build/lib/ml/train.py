"""Train a baseline severity classifier and log to MLflow.

label_severity is 0-4: CRITICAL=0, HIGH=1, MEDIUM=2, LOW=3, INFO=4 (same as ml.dataset.SEVERITY_TO_INT).
"""

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURE_COLS = ["rule_id", "resource_type", "has_public_cidr", "port", "service", "change_action"]
TARGET_COL = "label_severity"
CATEGORICAL_COLS = ["rule_id", "resource_type", "service", "change_action"]
NUMERIC_COLS = ["has_public_cidr", "port"]
DEFAULT_SEED = 42
TEST_SIZE = 0.2


def _prepare_data(df: pd.DataFrame):
    """Return X, y with has_public_cidr as int."""
    df = df.copy()
    if "has_public_cidr" in df.columns:
        df["has_public_cidr"] = df["has_public_cidr"].astype(int)
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    return X, y


def build_pipeline(model_type: str = "LogisticRegression"):
    """Build sklearn Pipeline with ColumnTransformer and classifier."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_COLS),
            ("num", "passthrough", NUMERIC_COLS),
        ],
    )
    if model_type == "RandomForest":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(random_state=DEFAULT_SEED, class_weight="balanced")
    else:
        clf = LogisticRegression(max_iter=5000, random_state=DEFAULT_SEED, class_weight="balanced")
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])


def run(
    csv_path: str | Path,
    model_out: str | Path,
    seed: int = DEFAULT_SEED,
    model_type: str = "LogisticRegression",
) -> dict:
    """
    Load CSV, train pipeline, log to MLflow, save model. Returns dict with metrics.
    """
    csv_path = Path(csv_path)
    model_out = Path(model_out)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if TARGET_COL not in df.columns or any(c not in df.columns for c in FEATURE_COLS):
        raise ValueError(f"CSV must contain columns: {FEATURE_COLS + [TARGET_COL]}")

    X, y = _prepare_data(df)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=seed, stratify=y
    )
    n_rows = len(df)

    pipeline = build_pipeline(model_type=model_type)
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    macro_f1 = f1_score(y_val, y_pred, average="macro", zero_division=0)
    # Per-class recall (0=CRITICAL .. 3=LOW .. 4=INFO); class 3 was under-represented
    recall_per_class = recall_score(y_val, y_pred, average=None, zero_division=0, labels=[0, 1, 2, 3, 4])
    recall_by_label = dict(zip([0, 1, 2, 3, 4], (float(r) for r in recall_per_class)))
    recall_class_3 = recall_by_label.get(3, 0.0)

    mlflow.set_experiment("driftguard-risk")
    run_id = None
    with mlflow.start_run():
        run_id = mlflow.active_run().info.run_id
        mlflow.log_params({
            "model_type": model_type,
            "seed": seed,
            "rows": n_rows,
            "class_weight": "balanced",
        })
        mlflow.log_metrics({
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "recall_class_3_low": recall_class_3,
        })

        cm = confusion_matrix(y_val, y_pred)
        fig, ax = plt.subplots()
        ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(cm)))
        ax.set_yticks(range(len(cm)))
        ax.set_xticklabels(range(len(cm)))
        ax.set_yticklabels(range(len(cm)))
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center")
        plt.title("Confusion matrix (label_severity)")
        plt.tight_layout()
        mlflow.log_figure(fig, "confusion_matrix.png")
        plt.close(fig)

        mlflow.sklearn.log_model(pipeline, artifact_path="model")

    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_out)
    if run_id:
        meta_path = model_out.with_suffix(model_out.suffix + ".meta.json")
        meta_path.write_text(json.dumps({"run_id": run_id}, indent=2), encoding="utf-8")

    return {"accuracy": accuracy, "macro_f1": macro_f1, "recall_class_3": recall_class_3, "rows": n_rows}
