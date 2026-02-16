"""Attach explanations and citations to findings using deterministic doc retrieval. No LLM."""

import json
from pathlib import Path

from scripts.retrieval import DOCS_DIR, get_sections, retrieve
from scripts.schemas import Citation, ExplainedFinding, ExplanationsReport, Finding, FindingsReport


def _format_snippet(sections: dict[str, str]) -> str:
    """Turn section dict into one markdown snippet (What / Why / How to fix / References)."""
    order = ("What this means", "Why it matters", "How to fix", "References")
    parts = []
    for title in order:
        if title in sections and sections[title].strip():
            parts.append(f"## {title}\n\n{sections[title].strip()}")
    return "\n\n".join(parts) if parts else ""


def explain_finding(finding: Finding, docs_dir: Path | None = None) -> ExplainedFinding:
    """Retrieve docs for finding.docs_keys, build explanation and citations."""
    docs_keys = finding.docs_keys or []
    retrieved = retrieve(docs_keys, sections_only=True, docs_dir=docs_dir or DOCS_DIR)

    snippets: list[str] = []
    citations: list[Citation] = []

    for key in docs_keys:
        if key not in retrieved:
            continue
        sections = retrieved[key]
        if isinstance(sections, dict):
            snippet = _format_snippet(sections)
        else:
            snippet = str(sections)
        if snippet:
            snippets.append(snippet)
        rel_path = f"docs/{key}.md"
        citations.append(Citation(doc_key=key, path=rel_path))

    explanation = "\n\n---\n\n".join(snippets)

    return ExplainedFinding(
        **finding.model_dump(),
        explanation=explanation,
        citations=citations,
    )


def run(
    findings_path: str | Path,
    output_path: str | Path,
    docs_dir: Path | None = None,
) -> ExplanationsReport:
    """Load findings.json, attach explanations and citations, write explanations.json."""
    path = Path(findings_path)
    if not path.exists():
        raise FileNotFoundError(f"Findings file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    report = FindingsReport.model_validate(data)

    explained = [explain_finding(f, docs_dir) for f in report.findings]
    out_report = ExplanationsReport(summary=report.summary, findings=explained)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_report.model_dump_json(indent=2), encoding="utf-8")

    return out_report
