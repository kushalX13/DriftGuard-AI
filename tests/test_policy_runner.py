"""Tests for policy_runner normalization (no conftest binary required)."""

import json
import pytest

from scripts.policy_runner import normalize_conftest_to_findings
from scripts.schemas import FindingsReport


def test_normalize_conftest_to_findings_empty() -> None:
    report = normalize_conftest_to_findings([])
    assert report.summary.critical == 0
    assert report.summary.high == 0
    assert len(report.findings) == 0


def test_normalize_conftest_to_findings_sg_and_s3() -> None:
    # Simulated Conftest -o json output
    conftest_results = [
        {
            "filename": "infra/tfplan.json",
            "success": False,
            "failures": [
                {
                    "msg": "Security group aws_security_group.open_ingress allows 0.0.0.0/0 on SSH (22) or RDP (3389): high risk"
                }
            ],
            "warnings": [
                {"msg": "S3 bucket aws_s3_bucket.bad_bucket has no server_side_encryption_configuration"}
            ],
        }
    ]
    report = normalize_conftest_to_findings(conftest_results)
    assert report.summary.critical == 1
    assert report.summary.high == 1
    assert len(report.findings) == 2

    sg = next(f for f in report.findings if f.id == "DG-SG-OPEN-SSH")
    assert sg.severity == "CRITICAL"
    assert sg.resource == "aws_security_group.open_ingress"
    assert "sg_open_ssh" in sg.docs_keys

    s3 = next(f for f in report.findings if f.id == "DG-S3-NO-ENCRYPTION")
    assert s3.severity == "HIGH"
    assert s3.resource == "aws_s3_bucket.bad_bucket"
    assert "s3_encryption" in s3.docs_keys


def test_normalize_new_rules() -> None:
    """S3 public block, SG 80/443, RDS encryption map to correct id and docs_key."""
    conftest_results = [
        {
            "warnings": [
                {"msg": "S3 bucket aws_s3_bucket.foo has no public access block (aws_s3_bucket_public_access_block)"},
                {"msg": "Security group aws_security_group.web allows 0.0.0.0/0 on HTTP (80) or HTTPS (443); consider WAF"},
                {"msg": "RDS instance aws_db_instance.main has storage_encrypted disabled"},
            ]
        }
    ]
    report = normalize_conftest_to_findings(conftest_results)
    assert len(report.findings) == 3
    ids = {f.id for f in report.findings}
    assert "DG-S3-NO-PUBLIC-ACCESS-BLOCK" in ids
    assert "DG-SG-OPEN-HTTP" in ids
    assert "DG-RDS-NO-ENCRYPTION" in ids
    s3_pub = next(f for f in report.findings if f.id == "DG-S3-NO-PUBLIC-ACCESS-BLOCK")
    assert "s3_public_access" in s3_pub.docs_keys
    rds = next(f for f in report.findings if f.id == "DG-RDS-NO-ENCRYPTION")
    assert "rds_encryption" in rds.docs_keys


def test_findings_report_serialization() -> None:
    from scripts.schemas import Finding, Summary

    report = FindingsReport(
        summary=Summary(critical=1, high=0, medium=0, low=0, info=0),
        findings=[
            Finding(
                id="DG-SG-OPEN-SSH",
                severity="CRITICAL",
                resource="aws_security_group.example",
                message="Security group allows 0.0.0.0/0 on port 22",
                evidence={"msg": "..."},
                docs_keys=["sg_open_ssh"],
            )
        ],
    )
    out = report.model_dump_json(indent=2)
    data = json.loads(out)
    assert data["summary"]["critical"] == 1
    assert len(data["findings"]) == 1
    assert data["findings"][0]["id"] == "DG-SG-OPEN-SSH"
    assert data["findings"][0]["docs_keys"] == ["sg_open_ssh"]
