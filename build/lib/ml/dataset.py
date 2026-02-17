"""Convert reports/findings.json into a tabular dataset (DataFrame / CSV) for training."""

import json
import re
from pathlib import Path

import pandas as pd

SEVERITY_TO_INT = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def _resource_type(resource: str) -> str:
    """Parse resource type from address (e.g. aws_security_group.open_ingress -> aws_security_group)."""
    if not resource or not isinstance(resource, str):
        return "unknown"
    part = resource.split(".")[0].strip()
    return part if part else "unknown"


def _has_public_cidr(message: str, evidence: dict) -> bool:
    """True if message or evidence mentions 0.0.0.0/0."""
    text = (message or "") + " " + json.dumps(evidence or {})
    return "0.0.0.0/0" in text


def _port(message: str, evidence: dict) -> int:
    """Extract 22 or 3389 if present in message/evidence else -1."""
    text = (message or "") + " " + json.dumps(evidence or {})
    if "22" in text and re.search(r"\b22\b", text):
        return 22
    if "3389" in text:
        return 3389
    return -1


def _service(resource_type: str, rule_id: str) -> str:
    """Infer service from resource_type or rule_id: s3, sg, iam, rds."""
    rt = (resource_type or "").lower()
    rid = (rule_id or "").lower()
    if "s3" in rt or "s3" in rid:
        return "s3"
    if "security_group" in rt or "sg" in rid:
        return "sg"
    if "iam" in rt or "iam" in rid:
        return "iam"
    if "db_instance" in rt or "rds" in rid:
        return "rds"
    return "other"


def _change_action(evidence: dict) -> str:
    """Extract create/update/delete from evidence if present else unknown."""
    if not evidence or not isinstance(evidence, dict):
        return "unknown"
    actions = evidence.get("actions")
    if isinstance(actions, list) and len(actions) > 0:
        a = actions[0]
        if isinstance(a, str) and a.lower() in ("create", "update", "delete"):
            return a.lower()
    change = evidence.get("change")
    if isinstance(change, dict):
        actions = change.get("actions")
        if isinstance(actions, list) and len(actions) > 0:
            a = actions[0]
            if isinstance(a, str) and a.lower() in ("create", "update", "delete"):
                return a.lower()
    return "unknown"


def _label_severity(severity: str) -> int:
    """Map CRITICAL/HIGH/MEDIUM/LOW/INFO to 0-4."""
    if not severity:
        return 4
    key = severity.upper().strip()
    return SEVERITY_TO_INT.get(key, 4)


def findings_to_dataframe(findings: list[dict]) -> pd.DataFrame:
    """Convert list of finding dicts to a DataFrame. Robust to missing fields."""
    rows = []
    for f in findings or []:
        resource = f.get("resource") or ""
        message = f.get("message") or ""
        evidence = f.get("evidence") if isinstance(f.get("evidence"), dict) else {}
        rule_id = f.get("id") or "unknown"
        severity = f.get("severity") or "INFO"
        resource_type = _resource_type(resource)
        rows.append({
            "rule_id": rule_id,
            "resource_type": resource_type,
            "has_public_cidr": _has_public_cidr(message, evidence),
            "port": _port(message, evidence),
            "service": _service(resource_type, rule_id),
            "change_action": _change_action(evidence),
            "label_severity": _label_severity(severity),
        })
    return pd.DataFrame(rows)


def load_findings(path: str | Path) -> list[dict]:
    """Load findings from JSON file. Returns list of finding dicts."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Findings file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    findings = data.get("findings")
    if not isinstance(findings, list):
        return []
    return findings


def run(findings_path: str | Path, out_path: str | Path) -> pd.DataFrame:
    """Load findings.json, build DataFrame, write CSV to out_path. Returns DataFrame."""
    findings = load_findings(findings_path)
    df = findings_to_dataframe(findings)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
