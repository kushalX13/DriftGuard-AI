"""Convert report.md to a self-contained HTML file for GitHub Pages."""

import re
from pathlib import Path

import markdown

# Human-friendly report UI: clear hierarchy, severity colors, readable cards
PAGE_CSS = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.65;
  color: #1f2937;
  max-width: 820px;
  margin: 0 auto;
  padding: 2.5rem 1.5rem 3rem;
  background: #f8fafc;
  font-size: 15px;
}
.report-header {
  margin-bottom: 1.5rem;
}
h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.25rem 0;
  color: #0f172a;
  letter-spacing: -0.02em;
}
.report-meta {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0.25rem 0 0.5rem 0;
}
.report-disclaimer {
  font-size: 0.85rem;
  color: #475569;
  margin: 0.5rem 0;
}
.report-takeaway {
  background: #e0f2fe;
  border-left: 4px solid #0284c7;
  padding: 0.65rem 1rem;
  margin: 1rem 0;
  border-radius: 0 6px 6px 0;
  font-size: 0.95rem;
  color: #0c4a6e;
}
h2 {
  font-size: 1.15rem;
  font-weight: 600;
  margin: 1.75rem 0 0.75rem 0;
  color: #0f172a;
  padding-bottom: 0.35rem;
  border-bottom: 2px solid #e2e8f0;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  border: 1px solid #e2e8f0;
}
th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { background: #f1f5f9; font-weight: 600; color: #334155; font-size: 0.9rem; }
tr:last-child td { border-bottom: 0; }
.findings-intro { margin: 0.5rem 0 0.75rem 0; color: #475569; font-size: 0.95rem; }
.findings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1rem;
  margin: 0.75rem 0;
}
details.finding {
  margin: 0;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
  min-height: 0;
}
details.finding.severity-critical { border-left: 4px solid #dc2626; }
details.finding.severity-high     { border-left: 4px solid #ea580c; }
details.finding.severity-medium  { border-left: 4px solid #ca8a04; }
details.finding.severity-low     { border-left: 4px solid #65a30d; }
details.finding.severity-info    { border-left: 4px solid #0891b2; }
details.finding summary {
  padding: 0.85rem 1rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.95rem;
  color: #1e293b;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
details.finding summary::-webkit-details-marker { display: none; }
details.finding summary::before {
  content: "▶";
  font-size: 0.65rem;
  color: #94a3b8;
  transition: transform 0.2s;
}
details.finding[open] summary::before { transform: rotate(90deg); }
details.finding[open] summary { border-bottom: 1px solid #e2e8f0; background: #fafafa; }
details.finding > div { padding: 1rem 1.25rem; }
details.finding h4 {
  font-size: 0.9rem;
  font-weight: 600;
  color: #475569;
  margin: 1rem 0 0.35rem 0;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
details.finding h4:first-of-type { margin-top: 0; }
details.finding ul { margin: 0.35rem 0; padding-left: 1.25rem; }
details.finding p { margin: 0.4rem 0; }
code {
  background: #f1f5f9;
  padding: 0.2em 0.45em;
  border-radius: 4px;
  font-size: 0.88em;
  color: #0f172a;
  border: 1px solid #e2e8f0;
}
pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.75rem 0;
  font-size: 0.85rem;
  line-height: 1.5;
  border: 1px solid #334155;
}
pre code { background: none; padding: 0; color: inherit; border: none; }
hr { border: 0; border-top: 1px solid #e2e8f0; margin: 1.5rem 0; }
a { color: #0369a1; text-decoration: none; }
a:hover { text-decoration: underline; }
"""


def _add_finding_classes(html: str) -> str:
    """Add class='finding severity-{level}' to each <details> based on summary content."""
    severity_map = [
        (r"CRITICAL", "critical"),
        (r"HIGH", "high"),
        (r"MEDIUM", "medium"),
        (r"LOW", "low"),
        (r"INFO", "info"),
    ]

    def replace_details(match):
        open_rest, inner, summary_content = match.group(1), match.group(2), match.group(3)
        severity = "medium"
        for pattern, level in severity_map:
            if re.search(pattern, summary_content):
                severity = level
                break
        return f'<details class="finding severity-{severity}"{open_rest}>{inner}<summary>{summary_content}</summary>'

    return re.sub(
        r"<details([^>]*)>(.*?)<summary>(.*?)</summary>",
        replace_details,
        html,
        flags=re.DOTALL,
    )


def convert(md_path: str | Path, out_path: str | Path, title: str = "DriftGuard Policy Report") -> Path:
    """Read markdown file, convert to HTML with template, write to out_path. Returns out_path."""
    md_path = Path(md_path)
    out_path = Path(out_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    raw = md_path.read_text(encoding="utf-8")
    # GitHub-style: tables, fenced code, nl2br; raw HTML (e.g. report-takeaway div) allowed
    html_body = markdown.markdown(
        raw,
        extensions=["tables", "fenced_code", "nl2br"],
        extension_configs={"tables": {}},
    )
    html_body = _add_finding_classes(html_body)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
{PAGE_CSS}
  </style>
</head>
<body>
{html_body}
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    import sys
    md = sys.argv[1] if len(sys.argv) > 1 else "reports/report.md"
    out = sys.argv[2] if len(sys.argv) > 2 else ".pages/index.html"
    convert(md, out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
