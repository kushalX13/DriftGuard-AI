"""Pydantic models for DriftGuard findings and report output."""

from typing import Any

from pydantic import BaseModel, Field


class Summary(BaseModel):
    """Counts per severity."""

    critical: int = Field(0, description="Critical findings count")
    high: int = Field(0, description="High findings count")
    medium: int = Field(0, description="Medium findings count")
    low: int = Field(0, description="Low findings count")
    info: int = Field(0, description="Info findings count")


class Finding(BaseModel):
    """Single normalized finding."""

    id: str = Field(..., description="Finding ID (e.g. DG-SG-OPEN-SSH)")
    severity: str = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW | INFO")
    resource: str = Field(..., description="Resource address (e.g. aws_security_group.example)")
    message: str = Field(..., description="Human-readable message")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Raw Conftest/OPA result")
    docs_keys: list[str] = Field(default_factory=list, description="Keys for remediation docs lookup")


class FindingsReport(BaseModel):
    """Normalized findings output (e.g. reports/findings.json)."""

    summary: Summary = Field(default_factory=Summary)
    findings: list[Finding] = Field(default_factory=list)


class Citation(BaseModel):
    """Reference to a remediation doc."""

    doc_key: str = Field(..., description="Key used for lookup (e.g. sg_open_ssh)")
    path: str = Field(..., description="Relative path to doc (e.g. docs/sg_open_ssh.md)")


class ExplainedFinding(Finding):
    """Finding with attached explanation text and citations (RAG output)."""

    explanation: str = Field("", description="Retrieved remediation text (sections or full doc)")
    citations: list[Citation] = Field(default_factory=list)


class ExplanationsReport(BaseModel):
    """Findings plus explanations and citations (e.g. reports/explanations.json)."""

    summary: Summary = Field(default_factory=Summary)
    findings: list[ExplainedFinding] = Field(default_factory=list)
