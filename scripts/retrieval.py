"""Deterministic doc retrieval: docs_keys -> markdown content or sections. No embeddings."""

import re
from pathlib import Path

# Keys map to filenames under docs/
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
SECTION_HEADERS = ("What this means", "Why it matters", "How to fix", "References")


def doc_path(doc_key: str) -> Path:
    """Return path to markdown file for a doc key (e.g. sg_open_ssh -> docs/sg_open_ssh.md)."""
    return DOCS_DIR / f"{doc_key}.md"


def get_doc(doc_key: str, docs_dir: Path | None = None) -> str:
    """Load full markdown content for a doc key. Raises FileNotFoundError if missing."""
    base = docs_dir or DOCS_DIR
    path = base / f"{doc_key}.md"
    if not path.exists():
        raise FileNotFoundError(f"Doc not found: {path}")
    return path.read_text(encoding="utf-8")


def get_sections(doc_key: str, docs_dir: Path | None = None) -> dict[str, str]:
    """Load markdown and return a dict of section title -> content (between ## headers)."""
    full = get_doc(doc_key, docs_dir)
    return _parse_sections(full)


def _parse_sections(markdown: str) -> dict[str, str]:
    """Split markdown by ## Section title and return dict. Section content is stripped."""
    # Match ## Title then content until next ## or end
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    parts = pattern.split(markdown)
    # parts[0] = content before first ##; parts[1]=title1, parts[2]=content1, ...
    result: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        content = parts[i + 1].strip()
        result[title] = content
    return result


def retrieve(doc_keys: list[str], sections_only: bool = False, docs_dir: Path | None = None) -> dict[str, str | dict[str, str]]:
    """
    For each doc key, load doc and return { doc_key: full_content } or { doc_key: sections_dict }.
    Missing keys are omitted (no exception).
    """
    base = docs_dir or DOCS_DIR
    out: dict[str, str | dict[str, str]] = {}
    for key in doc_keys:
        try:
            if sections_only:
                out[key] = get_sections(key, base)
            else:
                out[key] = get_doc(key, base)
        except FileNotFoundError:
            continue
    return out
