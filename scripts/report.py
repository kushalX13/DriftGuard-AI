"""Generate reports/report.md from findings + explanations (clean layout for PR/Pages)."""

import re
from datetime import datetime, timezone
from pathlib import Path

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


def _finding_section(finding: dict) -> str:
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


def build_markdown(data: dict, run_timestamp: datetime | None = None) -> str:
    """Build full report markdown from explanations report dict."""
    if run_timestamp is None:
        run_timestamp = datetime.now(timezone.utc)
    ts = run_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    summary = data.get("summary") or {}
    findings = data.get("findings") or []

    parts = [
        "# DriftGuard Policy Report",
        "",
        f"*Generated: {ts}*",
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
        parts.append(_finding_section(f))
        parts.append("")

    return "\n".join(parts).strip() + "\n"


def run(
    explanations_path: str | Path,
    output_path: str | Path,
    findings_path: str | Path | None = None,
) -> str:
    """
    Load explanations.json (or findings.json if explanations missing), generate report.md.
    Returns the generated markdown.
    """
    explanations_path = Path(explanations_path)
    output_path = Path(output_path)
    findings_path = Path(findings_path) if findings_path else output_path.parent / "findings.json"

    if explanations_path.exists():
        report = ExplanationsReport.model_validate_json(explanations_path.read_text(encoding="utf-8"))
        data = report.model_dump()
    elif findings_path.exists():
        findings_report = FindingsReport.model_validate_json(findings_path.read_text(encoding="utf-8"))
        data = findings_report.model_dump()
        # No explanation/citations; findings have empty explanation and citations
        for f in data.get("findings") or []:
            f.setdefault("explanation", "")
            f.setdefault("citations", [])
    else:
        raise FileNotFoundError(
            f"Neither explanations nor findings file found. Tried: {explanations_path}, {findings_path}"
        )

    markdown = build_markdown(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown
