"""Attach explanations and citations to findings using deterministic doc retrieval. Optional LLM humanize."""

import json
import os
import sys
from pathlib import Path

from scripts.retrieval import DOCS_DIR, get_sections, retrieve
from scripts.schemas import Citation, ExplainedFinding, ExplanationsReport, Finding, FindingsReport


def _humanize_with_llm(explanation: str, message: str, resource: str) -> str:
    """Rewrite explanation in a friendly, conversational way. No-op if openai or API key missing."""
    try:
        from openai import OpenAI
    except ImportError:
        return explanation
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not explanation.strip():
        return explanation
    client = OpenAI(api_key=api_key)
    prompt = (
        "You are a helpful security engineer. Rewrite the following policy finding explanation "
        "so it's clear and conversational for a developer. Keep all facts and remediation steps; "
        "only change tone to be friendly and direct. Use simple markdown (bold, lists) if it helps. "
        "Do not add extra sections or headers.\n\n"
        f"Finding: {resource} — {message}\n\n"
        "Current explanation:\n"
        f"{explanation}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You rewrite technical security text to be clear and friendly. Output only the rewritten explanation, no preamble."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
        )
        if resp.choices and resp.choices[0].message.content:
            return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM humanize warning: {e}", file=sys.stderr)
    return explanation


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
    use_llm: bool = False,
) -> ExplanationsReport:
    """Load findings.json, attach explanations and citations, write explanations.json. Optionally humanize with LLM."""
    path = Path(findings_path)
    if not path.exists():
        raise FileNotFoundError(f"Findings file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    report = FindingsReport.model_validate(data)

    explained = [explain_finding(f, docs_dir) for f in report.findings]
    if use_llm:
        try:
            from openai import OpenAI
            has_openai = True
        except ImportError:
            has_openai = False
        api_key = os.environ.get("OPENAI_API_KEY")
        if not has_openai:
            print("Warning: install with pip install '.[llm]' to use --use-llm.", file=sys.stderr)
        elif not api_key:
            print("Warning: OPENAI_API_KEY not set (e.g. in .env). Explanations are from docs only.", file=sys.stderr)
        else:
            n = len(explained)
            print(f"Humanizing {n} finding(s) with OpenAI...", file=sys.stderr)
        humanized = []
        for ef in explained:
            new_explanation = _humanize_with_llm(
                ef.explanation, ef.message, ef.resource or ""
            )
            humanized.append(ef.model_copy(update={"explanation": new_explanation}))
        explained = humanized
    out_report = ExplanationsReport(summary=report.summary, findings=explained)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_report.model_dump_json(indent=2), encoding="utf-8")

    return out_report
