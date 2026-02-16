"""Generate reports/report.md from findings + explanations (clean layout for PR/Pages)."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.schemas import ExplanationsReport, FindingsReport


def _parse_explanation_sections(explanation: str) -> dict[str, str]:
    """Extract section content by ## Title. Returns dict of title -> content."""
    if not explanation or not explanation.strip():
        return {}
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    parts = pattern.split(explanation.strip())
    result: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        content = parts[i + 1].strip()
        result[title] = content
    return result


def _summary_table(summary: dict) -> str:
    """Markdown table of severity counts."""
    return """| Severity | Count |
|---------|-------|
| Critical | %(critical)s |
| High | %(high)s |
| Medium | %(medium)s |
| Low | %(low)s |
| Info | %(info)s |
""" % {
        "critical": summary.get("critical", 0),
        "high": summary.get("high", 0),
        "medium": summary.get("medium", 0),
        "low": summary.get("low", 0),
        "info": summary.get("info", 0),
    }


def _finding_section(finding: dict, score: dict | None = None) -> str:
    """One collapsible section for a finding (GitHub <details>/<summary>)."""
    severity = finding.get("severity", "INFO")
    resource = finding.get("resource", "—")
    message = finding.get("message", "")
    rule_id = finding.get("id", "")
    explanation = finding.get("explanation", "")
    citations = finding.get("citations") or []

    summary_line = f"**{severity}** — `{resource}` — {message}"
    if len(summary_line) > 100:
        summary_line = summary_line[:97] + "…"

    sections = _parse_explanation_sections(explanation)
    why = sections.get("Why it matters", "").strip()
    how = sections.get("How to fix", "").strip()

    body_parts = [
        f"- **Resource:** `{resource}`",
        f"- **Rule:** `{rule_id}`",
        f"- **Message:** {message}",
        "",
    ]
    if score:
        conf = score.get("confidence")
        low_confidence = isinstance(conf, (int, float)) and conf < 0.6
        if low_confidence:
            body_parts.append("- **Predicted severity:** (low confidence)")
        else:
            body_parts.append(f"- **Predicted severity:** {score.get('predicted_severity', '—')}")
        if not low_confidence:
            rs = score.get("risk_score")
            body_parts.append(f"- **Risk score:** {rs:.2f}" if isinstance(rs, (int, float)) else "- **Risk score:** —")
            if isinstance(conf, (int, float)):
                body_parts.append(f"- **Confidence:** {conf:.2f}")
        body_parts.append("")
    if why:
        body_parts.append("#### Why it matters\n")
        body_parts.append(why)
        body_parts.append("")
    if how:
        body_parts.append("#### How to fix\n")
        body_parts.append(how)
        body_parts.append("")
    if not why and not how and explanation:
        body_parts.append("#### Details\n")
        body_parts.append(explanation)
        body_parts.append("")
    if citations:
        body_parts.append("#### References\n")
        for c in citations:
            path = c.get("path", f"docs/{c.get('doc_key', '')}.md")
            key = c.get("doc_key", path)
            body_parts.append(f"- [{key}]({path})")
        body_parts.append("")

    body = "\n".join(body_parts)
    return f"""<details>
<summary>{summary_line}</summary>

{body}
</details>
"""


def _finding_key(finding: dict) -> str:
    """Stable key for joining risk_scores to findings. Must match ml.predict._finding_key."""
    fid = finding.get("id") or ""
    resource = finding.get("resource") or ""
    return f"{fid}::{resource}"


def build_markdown(
    data: dict,
    run_timestamp: datetime | None = None,
    risk_scores_by_key: dict[str, dict] | None = None,
) -> str:
    """Build full report markdown. risk_scores_by_key maps finding_key -> {predicted_severity, risk_score}."""
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.replace(tzinfo=timezone.utc)
    est = run_timestamp.astimezone(ZoneInfo("America/New_York"))
    ts = est.strftime("%Y-%m-%d %H:%M:%S ET")

    summary = data.get("summary") or {}
    findings = data.get("findings") or []
    by_key = risk_scores_by_key or {}

    parts = [
        "# DriftGuard Policy Report",
        "",
        f"*Generated: {ts}*",
        "",
        "**Policy severity is authoritative. ML risk scoring is experimental and may disagree.**",
        "",
        "---",
        "",
        "## Summary",
        "",
        _summary_table(summary),
        "---",
        "",
        "## Findings",
        "",
    ]
    for f in findings:
        key = _finding_key(f)
        score = by_key.get(key)
        parts.append(_finding_section(f, score))
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def run(
    explanations_path: str | Path,
    output_path: str | Path,
    findings_path: str | Path | None = None,
    risk_scores_path: str | Path | None = None,
    include_risk_scores: bool = True,
) -> str:
    """
    Load explanations.json (or findings.json if explanations missing), optionally risk_scores.json.
    Generate report.md. Returns the generated markdown.
    When include_risk_scores is False (e.g. policy-only run), risk scores are not loaded.
    """
    explanations_path = Path(explanations_path)
    output_path = Path(output_path)
    findings_path = Path(findings_path) if findings_path else output_path.parent / "findings.json"
    path_for_scores = Path(risk_scores_path) if risk_scores_path else output_path.parent / "risk_scores.json"

    if explanations_path.exists():
        report = ExplanationsReport.model_validate_json(explanations_path.read_text(encoding="utf-8"))
        data = report.model_dump()
    elif findings_path.exists():
        findings_report = FindingsReport.model_validate_json(findings_path.read_text(encoding="utf-8"))
        data = findings_report.model_dump()
        for f in data.get("findings") or []:
            f.setdefault("explanation", "")
            f.setdefault("citations", [])
    else:
        raise FileNotFoundError(
            f"Neither explanations nor findings file found. Tried: {explanations_path}, {findings_path}"
        )

    risk_scores_by_key: dict[str, dict] = {}
    if include_risk_scores and path_for_scores.exists():
        try:
            raw = json.loads(path_for_scores.read_text(encoding="utf-8"))
            for s in raw.get("scores") or []:
                key = s.get("finding_key")
                if key:
                    risk_scores_by_key[key] = s
        except (json.JSONDecodeError, OSError):
            pass

    markdown = build_markdown(data, risk_scores_by_key=risk_scores_by_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown
