"""Generate reports/report.md from findings + explanations (clean layout for PR/Pages)."""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown
from scripts.schemas import ExplanationsReport, FindingsReport


def _escape(s: str) -> str:
    return html.escape(str(s), quote=True)


def _md(s: str) -> str:
    """Render markdown to HTML (bold, lists, code, links) for display."""
    if not s or not s.strip():
        return ""
    return markdown.markdown(s.strip(), extensions=["nl2br", "fenced_code"], output_format="html5").strip()


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
    """One collapsible section: clean HTML only (no raw markdown * or `)."""
    severity = finding.get("severity", "INFO")
    resource = finding.get("resource", "—")
    message = finding.get("message", "")
    rule_id = finding.get("id", "")
    explanation = finding.get("explanation", "")
    citations = finding.get("citations") or []

    r = _escape(resource)
    msg_esc = _escape(message)
    # Truncate only if very long; break at word boundary so it doesn't look cut off
    max_msg = 180
    if len(msg_esc) > max_msg:
        cut = msg_esc[: max_msg + 1].rfind(" ")
        msg_short = (msg_esc[: cut] if cut > max_msg // 2 else msg_esc[: max_msg]) + "…"
    else:
        msg_short = msg_esc
    summary_html = f'<span class="severity-badge severity-{severity.lower()}">{_escape(severity)}</span> <code class="resource-id">{r}</code> <span class="summary-msg">— {msg_short}</span>'

    sections = _parse_explanation_sections(explanation)
    why = sections.get("Why it matters", "").strip()
    how = sections.get("How to fix", "").strip()

    lines = [
        "<ul class=\"finding-meta\">",
        f"<li><strong>Resource</strong> <code>{r}</code></li>",
        f"<li><strong>Rule</strong> <code>{_escape(rule_id)}</code></li>",
        f"<li><strong>Message</strong> {_escape(message)}</li>",
    ]
    if score:
        conf = score.get("confidence")
        low_confidence = isinstance(conf, (int, float)) and conf < 0.6
        if low_confidence:
            lines.append("<li><strong>Predicted severity</strong> (low confidence)</li>")
        else:
            lines.append(f"<li><strong>Predicted severity</strong> {_escape(str(score.get('predicted_severity', '—')))}</li>")
        if not low_confidence:
            rs = score.get("risk_score")
            if isinstance(rs, (int, float)):
                lines.append(f"<li><strong>Risk score</strong> {rs:.2f}</li>")
            if isinstance(conf, (int, float)):
                lines.append(f"<li><strong>Confidence</strong> {conf:.2f}</li>")
    lines.append("</ul>")

    if why:
        lines.append('<h4>Why it matters</h4>')
        lines.append(f'<div class="finding-body">{_md(why)}</div>')
    if how:
        lines.append('<h4>How to fix</h4>')
        lines.append(f'<div class="finding-body">{_md(how)}</div>')
    if not why and not how and explanation:
        lines.append('<h4>Details</h4>')
        lines.append(f'<div class="finding-body">{_md(explanation)}</div>')
    if citations:
        lines.append("<h4>References</h4>")
        lines.append("<ul>")
        for c in citations:
            path = c.get("path", f"docs/{c.get('doc_key', '')}.md")
            key = _escape(c.get("doc_key", path))
            lines.append(f'<li><a href="{_escape(path)}">{key}</a></li>')
        lines.append("</ul>")

    body = "\n".join(lines)
    sev = severity.lower()
    return f"<details class=\"finding severity-{sev}\">\n<summary>{summary_html}</summary>\n<div class=\"finding-inner\">\n{body}\n</div>\n</details>"


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
    total = sum(summary.get(k, 0) for k in ("critical", "high", "medium", "low", "info"))

    parts = [
        "# DriftGuard Policy Report",
        "",
        f'<p class="report-meta">*Generated: {ts}*</p>',
        "",
        '<p class="report-disclaimer">**Policy severity is authoritative. ML risk scoring is experimental and may disagree.**</p>',
        "",
        ('<div class="report-takeaway">We found ' + str(total) + ' issue(s). Fix Critical and High first, then review the rest.</div>' if total else '<div class="report-takeaway">No policy issues found.</div>'),
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
    if findings:
        parts.append('<div class="findings-grid">')
    for f in findings:
        key = _finding_key(f)
        score = by_key.get(key)
        parts.append(_finding_section(f, score))
        parts.append("")
    if findings:
        parts.append("</div>")

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
