"""Tests for explain: attach explanations and citations to findings."""

import json
from pathlib import Path

import pytest

from scripts.explain import explain_finding, run
from scripts.schemas import Finding


def test_explain_finding_sg() -> None:
    f = Finding(
        id="DG-SG-OPEN-SSH",
        severity="CRITICAL",
        resource="aws_security_group.open_ingress",
        message="Security group allows 0.0.0.0/0 on port 22",
        evidence={},
        docs_keys=["sg_open_ssh"],
    )
    explained = explain_finding(f)
    assert explained.explanation
    assert "What this means" in explained.explanation
    assert "How to fix" in explained.explanation
    assert len(explained.citations) == 1
    assert explained.citations[0].doc_key == "sg_open_ssh"
    assert explained.citations[0].path == "docs/sg_open_ssh.md"


def test_explain_finding_s3() -> None:
    f = Finding(
        id="DG-S3-NO-ENCRYPTION",
        severity="HIGH",
        resource="aws_s3_bucket.bad_bucket",
        message="S3 bucket has no encryption",
        evidence={},
        docs_keys=["s3_encryption"],
    )
    explained = explain_finding(f)
    assert explained.explanation
    assert "server-side encryption" in explained.explanation.lower()
    assert explained.citations[0].doc_key == "s3_encryption"


def test_explain_run_roundtrip(tmp_path: Path) -> None:
    findings = {
        "summary": {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0},
        "findings": [
            {
                "id": "DG-SG-OPEN-SSH",
                "severity": "CRITICAL",
                "resource": "aws_security_group.example",
                "message": "Security group allows 0.0.0.0/0 on port 22",
                "evidence": {},
                "docs_keys": ["sg_open_ssh"],
            }
        ],
    }
    findings_file = tmp_path / "findings.json"
    findings_file.write_text(json.dumps(findings), encoding="utf-8")
    out_file = tmp_path / "explanations.json"

    report = run(findings_file, out_file)
    assert len(report.findings) == 1
    assert report.findings[0].explanation
    assert report.findings[0].citations

    data = json.loads(out_file.read_text())
    assert "summary" in data
    assert len(data["findings"]) == 1
    assert "explanation" in data["findings"][0]
    assert "citations" in data["findings"][0]
