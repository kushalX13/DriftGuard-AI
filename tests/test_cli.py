"""Minimal CLI tests."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scripts.cli import _should_fail_on, app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "plan" in result.output
    assert "policy" in result.output
    assert "report" in result.output
    assert "run" in result.output


def test_plan_help() -> None:
    result = runner.invoke(app, ["plan", "--help"])
    assert result.exit_code == 0
    assert "tf-dir" in result.output
    assert "fallback-sample" in result.output
    assert "out" in result.output


def test_should_fail_on_critical(tmp_path: Path) -> None:
    findings = tmp_path / "findings.json"
    findings.write_text('{"summary": {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0}, "findings": []}')
    should, msg = _should_fail_on(findings, "critical")
    assert should is True
    assert "critical" in msg


def test_should_fail_on_none(tmp_path: Path) -> None:
    findings = tmp_path / "findings.json"
    findings.write_text('{"summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, "findings": []}')
    should, msg = _should_fail_on(findings, "critical")
    assert should is False
    assert msg == ""


def test_run_help_includes_fail_on() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "fail-on" in result.output
    assert "FAIL_ON" in result.output
