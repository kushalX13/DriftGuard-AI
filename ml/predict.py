"""Run trained severity model on findings and write reports/risk_scores.json.

If ml/models/severity_model.pkl is missing, callers skip inference (no error).
Scores include a stable finding_key (id::resource) so report can join by key, not index.
Uses same feature columns as ml.train (no mlflow dependency here).
"""


def _finding_key(finding: dict) -> str:
    """Stable key for joining scores to findings. Deterministic: id + '::' + resource."""
    fid = finding.get("id") or ""
    resource = finding.get("resource") or ""
    return f"{fid}::{resource}"

import json
from datetime import datetime, timezone
from pathlib import Path

# Must match ml.train.FEATURE_COLS so saved pipeline gets same columns
FEATURE_COLS = ["rule_id", "resource_type", "has_public_cidr", "port", "service", "change_action"]
INT_TO_SEVERITY = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
# Weights for expected-risk: risk_score = sum(p(class) * weight(class))
SEVERITY_WEIGHTS = (1.0, 0.75, 0.5, 0.25, 0.1)


def run(
    findings_path: str | Path,
    model_path: str | Path,
    output_path: str | Path,
) -> bool:
    """
    Load model and findings, run inference, write risk_scores.json.
    Returns True if inference ran and file was written; False if model missing or any error (skip gracefully).
    """
    model_path = Path(model_path)
    if not model_path.exists():
        return False

    try:
        import joblib
        from ml.dataset import findings_to_dataframe, load_findings
    except ImportError:
        return False

    try:
        findings = load_findings(findings_path)
    except (FileNotFoundError, OSError):
        return False
    def _meta(model_path: Path) -> dict:
        """Model versioning: path, generated_at, run_id (if sidecar exists)."""
        meta = {
            "model": str(model_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        sidecar = model_path.with_suffix(model_path.suffix + ".meta.json")
        if sidecar.exists():
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                if data.get("run_id"):
                    meta["run_id"] = data["run_id"]
            except (json.JSONDecodeError, OSError):
                pass
        return meta

    if not findings:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {**_meta(model_path), "scores": []}
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True

    try:
        df = findings_to_dataframe(findings)
        for c in FEATURE_COLS:
            if c not in df.columns:
                return False
        if "has_public_cidr" in df.columns:
            df = df.copy()
            df["has_public_cidr"] = df["has_public_cidr"].astype(int)
        X = df[FEATURE_COLS]

        pipeline = joblib.load(model_path)
        preds = pipeline.predict(X)
        n = len(preds)
        if hasattr(pipeline, "predict_proba"):
            proba = pipeline.predict_proba(X)
            risk_scores = []
            confidences = []
            for i in range(n):
                p_vec = proba[i]
                n_classes = min(len(p_vec), len(SEVERITY_WEIGHTS))
                risk = sum(float(p_vec[c]) * SEVERITY_WEIGHTS[c] for c in range(n_classes))
                risk_scores.append(risk)
                confidences.append(float(p_vec.max()))
        else:
            risk_scores = [
                SEVERITY_WEIGHTS[int(p)] if 0 <= int(p) < len(SEVERITY_WEIGHTS) else 0.1
                for p in preds
            ]
            confidences = [1.0] * n

        scores = [
            {
                "finding_key": _finding_key(findings[i]),
                "predicted_severity": INT_TO_SEVERITY[int(p)] if 0 <= p < len(INT_TO_SEVERITY) else "INFO",
                "risk_score": risk_scores[i],
                "confidence": confidences[i],
            }
            for i, p in enumerate(preds)
        ]

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {**_meta(model_path), "scores": scores}
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
