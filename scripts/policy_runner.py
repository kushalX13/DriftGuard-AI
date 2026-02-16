"""Run Conftest on tfplan.json and normalize output to findings schema."""

import json
import re
import subprocess
from pathlib import Path

from scripts.schemas import Finding, FindingsReport, Summary


def run_conftest(plan_path: str | Path, policy_path: str | Path) -> list[dict]:
    """Run conftest test -o json and return parsed results (list of result objects)."""
    plan_path = Path(plan_path)
    policy_path = Path(policy_path)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy path not found: {policy_path}")

    cmd = [
        "conftest",
        "test",
        str(plan_path),
        "-p",
        str(policy_path),
        "-o",
        "json",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    raw = (result.stdout or "").strip()
    if not raw:
        raw = (result.stderr or "").strip()
    if not raw:
        raise ValueError(
            f"Conftest produced no output (exit {result.returncode}). "
            "Run: conftest test infra/tfplan.json -p policies/rego -o json"
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Conftest output is not valid JSON: {e}. "
            "Some Conftest versions write -o json to stderr; check your version."
        ) from e
    # Conftest returns array of results per file, or a single object
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


# Message patterns -> (finding_id, severity, docs_key). Order matters: more specific first.
PATTERNS = [
    (
        re.compile(r"Security group (.+?) allows .*0\.0\.0\.0/0.*(?:SSH|22|3389|RDP)", re.I),
        "DG-SG-OPEN-SSH",
        "CRITICAL",
        "sg_open_ssh",
    ),
    (
        re.compile(r"Security group (.+?) allows .*0\.0\.0\.0/0.*(?:HTTP|80|443|HTTPS)", re.I),
        "DG-SG-OPEN-HTTP",
        "MEDIUM",
        "sg_open_http",
    ),
    (
        re.compile(r"S3 bucket (.+?) has no server_side_encryption", re.I),
        "DG-S3-NO-ENCRYPTION",
        "HIGH",
        "s3_encryption",
    ),
    (
        re.compile(r"S3 bucket (.+?) has no public access block", re.I),
        "DG-S3-NO-PUBLIC-ACCESS-BLOCK",
        "HIGH",
        "s3_public_access",
    ),
    (
        re.compile(r"RDS instance (.+?) has storage_encrypted disabled", re.I),
        "DG-RDS-NO-ENCRYPTION",
        "HIGH",
        "rds_encryption",
    ),
]


def _resource_and_meta(message: str) -> tuple[str, str, str, str]:
    """Extract resource address, finding id, severity, docs_key from message. Defaults if no match."""
    for pattern, fid, sev, doc_key in PATTERNS:
        m = pattern.search(message)
        if m:
            return m.group(1).strip(), fid, sev, doc_key
    return "unknown", "DG-UNKNOWN", "MEDIUM", "general"


def _normalize_item(msg: str, raw: dict, severity_override: str | None) -> Finding:
    """Build one Finding from a Conftest failure/warning item."""
    resource, finding_id, severity, doc_key = _resource_and_meta(msg)
    if severity_override:
        severity = severity_override
    return Finding(
        id=finding_id,
        severity=severity,
        resource=resource,
        message=msg,
        evidence=raw,
        docs_keys=[doc_key],
    )


def normalize_conftest_to_findings(conftest_results: list[dict]) -> FindingsReport:
    """Map Conftest JSON results to FindingsReport."""
    findings: list[Finding] = []

    for file_result in conftest_results:
        failures = file_result.get("failures") or []
        warnings = file_result.get("warnings") or []
        for item in failures:
            msg = item.get("msg", item) if isinstance(item, dict) else str(item)
            if msg:
                evidence = item if isinstance(item, dict) else {"raw": item}
                findings.append(_normalize_item(msg, evidence, "CRITICAL"))
        for item in warnings:
            msg = item.get("msg", item) if isinstance(item, dict) else str(item)
            if msg:
                evidence = item if isinstance(item, dict) else {"raw": item}
                findings.append(_normalize_item(msg, evidence, None))

    # Build summary counts
    summary = Summary()
    for f in findings:
        key = f.severity.lower()
        if key in summary.model_fields:
            setattr(summary, key, getattr(summary, key) + 1)

    return FindingsReport(summary=summary, findings=findings)


def run(
    plan_path: str | Path,
    policy_path: str | Path,
    output_path: str | Path,
) -> FindingsReport:
    """Run Conftest, normalize, write findings.json; return FindingsReport."""
    results = run_conftest(plan_path, policy_path)
    report = normalize_conftest_to_findings(results)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    return report
