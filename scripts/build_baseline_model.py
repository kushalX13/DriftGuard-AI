"""Build a minimal severity model for CI/demo (no MLflow). Saves to ml/models/severity_model.pkl.

Run once and commit ml/models/ so CI can show ML scoring without running the Train workflow.
Uses same pipeline shape as ml.train so predict works.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.generate_synthetic import generate_synthetic

# Must match ml.train
FEATURE_COLS = ["rule_id", "resource_type", "has_public_cidr", "port", "service", "change_action"]
TARGET_COL = "label_severity"
CATEGORICAL_COLS = ["rule_id", "resource_type", "service", "change_action"]
NUMERIC_COLS = ["has_public_cidr", "port"]

BASELINE_ROWS = 200
MODEL_DIR = Path(__file__).resolve().parent.parent / "ml" / "models"
MODEL_PATH = MODEL_DIR / "severity_model.pkl"


def _build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_COLS),
            ("num", "passthrough", NUMERIC_COLS),
        ],
    )
    clf = LogisticRegression(max_iter=5000, random_state=42)
    return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])


def main() -> None:
    df = generate_synthetic(n_rows=BASELINE_ROWS, seed=42)
    if TARGET_COL not in df.columns or any(c not in df.columns for c in FEATURE_COLS):
        raise ValueError(f"Generated CSV must have {FEATURE_COLS + [TARGET_COL]}")
    if "has_public_cidr" in df.columns:
        df = df.copy()
        df["has_public_cidr"] = df["has_public_cidr"].astype(int)
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    pipeline = _build_pipeline()
    pipeline.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    meta_path = MODEL_PATH.with_suffix(MODEL_PATH.suffix + ".meta.json")
    meta_path.write_text(json.dumps({"run_id": "baseline"}, indent=2), encoding="utf-8")
    print(f"Saved {MODEL_PATH} and {meta_path} (n_rows={BASELINE_ROWS})")


if __name__ == "__main__":
    main()
