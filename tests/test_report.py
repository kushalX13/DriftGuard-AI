"""Tests for report markdown generation."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.report import build_markdown, run


def test_build_markdown_summary_table() -> None:
    data = {
        "summary": {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 0},
        "findings": [],
    }
    md = build_markdown(data, run_timestamp=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc))
    assert "DriftGuard Policy Report" in md
    assert "2025-06-01 12:00:00 UTC" in md
    assert "| Critical | 1 |" in md
    assert "| High | 1 |" in md
    assert "## Summary" in md
    assert "## Findings" in md


def test_build_markdown_finding_collapsible() -> None:
    data = {
        "summary": {"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
        "findings": [
            {
                "id": "DG-S3-NO-ENCRYPTION",
                "severity": "HIGH",
                "resource": "aws_s3_bucket.bad_bucket",
                "message": "S3 bucket has no encryption",
                "evidence": {},
                "docs_keys": ["s3_encryption"],
                "explanation": "## Why it matters\n\nData at rest should be encrypted.\n\n## How to fix\n\nAdd server_side_encryption_configuration.",
                "citations": [{"doc_key": "s3_encryption", "path": "docs/s3_encryption.md"}],
            }
        ],
    }
    md = build_markdown(data)
    assert "<details>" in md
    assert "<summary>" in md
    assert "**HIGH**" in md
    assert "aws_s3_bucket.bad_bucket" in md
    assert "Why it matters" in md
    assert "How to fix" in md
    assert "[s3_encryption](docs/s3_encryption.md)" in md


def test_report_run_roundtrip(tmp_path: Path) -> None:
    import json

    explanations = {
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        "findings": [],
    }
    ex_path = tmp_path / "explanations.json"
    ex_path.write_text(json.dumps(explanations), encoding="utf-8")
    out_path = tmp_path / "report.md"

    run(ex_path, out_path)
    content = out_path.read_text()
    assert "DriftGuard Policy Report" in content
    assert "## Summary" in content
