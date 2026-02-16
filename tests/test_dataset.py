"""Tests for ml.dataset (findings -> DataFrame/CSV)."""

import json
from pathlib import Path

import pytest

from ml.dataset import (
    _change_action,
    _has_public_cidr,
    _label_severity,
    _port,
    _resource_type,
    _service,
    findings_to_dataframe,
    load_findings,
    run,
)


def test_resource_type() -> None:
    assert _resource_type("aws_security_group.open_ingress") == "aws_security_group"
    assert _resource_type("aws_s3_bucket.bad_bucket") == "aws_s3_bucket"
    assert _resource_type("") == "unknown"


def test_has_public_cidr() -> None:
    assert _has_public_cidr("allows 0.0.0.0/0", {}) is True
    assert _has_public_cidr("no cidr", {}) is False
    assert _has_public_cidr("", {"msg": "cidr 0.0.0.0/0"}) is True


def test_port() -> None:
    assert _port("port 22 SSH", {}) == 22
    assert _port("RDP 3389", {}) == 3389
    assert _port("no port", {}) == -1


def test_service() -> None:
    assert _service("aws_s3_bucket", "DG-S3-NO-ENCRYPTION") == "s3"
    assert _service("aws_security_group", "DG-SG-OPEN-SSH") == "sg"
    assert _service("aws_db_instance", "DG-RDS-NO-ENCRYPTION") == "rds"


def test_change_action() -> None:
    assert _change_action({"actions": ["create"]}) == "create"
    assert _change_action({"change": {"actions": ["update"]}}) == "update"
    assert _change_action({}) == "unknown"


def test_label_severity() -> None:
    assert _label_severity("CRITICAL") == 0
    assert _label_severity("HIGH") == 1
    assert _label_severity("INFO") == 4
    assert _label_severity("") == 4


def test_findings_to_dataframe() -> None:
    findings = [
        {
            "id": "DG-SG-OPEN-SSH",
            "severity": "CRITICAL",
            "resource": "aws_security_group.open_ingress",
            "message": "allows 0.0.0.0/0 on port 22",
            "evidence": {},
            "docs_keys": ["sg_open_ssh"],
        }
    ]
    df = findings_to_dataframe(findings)
    assert len(df) == 1
    assert df["rule_id"].iloc[0] == "DG-SG-OPEN-SSH"
    assert df["resource_type"].iloc[0] == "aws_security_group"
    assert df["has_public_cidr"].iloc[0] == True  # noqa: E712
    assert df["port"].iloc[0] == 22
    assert df["service"].iloc[0] == "sg"
    assert df["label_severity"].iloc[0] == 0


def test_run_roundtrip(tmp_path: Path) -> None:
    findings_file = tmp_path / "findings.json"
    findings_file.write_text(
        json.dumps({
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "findings": [
                {"id": "DG-S3-NO-ENCRYPTION", "severity": "HIGH", "resource": "aws_s3_bucket.foo", "message": "no encryption", "evidence": {}, "docs_keys": []}
            ],
        }),
        encoding="utf-8",
    )
    out_csv = tmp_path / "ml" / "data" / "findings.csv"
    df = run(findings_file, out_csv)
    assert len(df) == 1
    assert out_csv.exists()
    assert df["service"].iloc[0] == "s3"
    assert df["label_severity"].iloc[0] == 1
