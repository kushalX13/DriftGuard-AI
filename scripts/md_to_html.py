"""Convert report.md to a self-contained HTML file for GitHub Pages."""

import re
from pathlib import Path

import markdown

# Polished report UI: dashboard-style hierarchy, severity accents, readable cards
PAGE_CSS = """
* { box-sizing: border-box; }
body {
  font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.6;
  color: #1e293b;
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0 2rem 4rem;
  background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
  font-size: 15px;
  min-height: 100vh;
}
.report-header { margin-bottom: 0; }
h1 {
  font-size: 1.85rem;
  font-weight: 700;
  margin: 0;
  color: #0f172a;
  letter-spacing: -0.03em;
  padding: 1.75rem 2rem 0.75rem;
  background: #fff;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 1px 0 0 #e2e8f0;
}
.report-meta {
  color: #64748b;
  font-size: 0.875rem;
  margin: 0;
  padding: 0 2rem 0.25rem;
  background: #fff;
}
.report-disclaimer {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
  padding: 0 2rem 1.25rem;
  background: #fff;
}
.report-takeaway {
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  color: #fff;
  padding: 1rem 2rem;
  margin: 0;
  border-radius: 0 0 12px 12px;
  font-size: 1rem;
  font-weight: 500;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.25);
  letter-spacing: 0.01em;
}
.report-takeaway + hr { margin-top: 1.5rem; }
h2 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 2rem 0 1rem 0;
  color: #0f172a;
  padding-bottom: 0.5rem;
  border-bottom: none;
  letter-spacing: -0.01em;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0 0 1.5rem 0;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,.07);
  border: 1px solid rgba(0,0,0,.06);
}
th, td { padding: 0.75rem 1.25rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
th { background: #f8fafc; font-weight: 600; color: #475569; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
tr:last-child td { border-bottom: 0; }
tr:hover td { background: #fafbfc; }
.findings-intro { margin: 0.5rem 0 1rem 0; color: #64748b; font-size: 0.95rem; }
.findings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1.5rem;
  margin: 1.25rem 0 0 0;
  width: 100%;
  max-width: 100%;
  align-items: start;
}
details.finding {
  margin: 0;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 4px 12px rgba(0,0,0,.04);
  min-height: 0;
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.15s ease;
}
details.finding:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,.08), 0 12px 28px rgba(0,0,0,.06);
  border-color: #cbd5e1;
}
details.finding[open] {
  box-shadow: 0 4px 12px rgba(0,0,0,.08), 0 12px 28px rgba(0,0,0,.06);
  border-color: #cbd5e1;
}
details.finding.severity-critical { border-left: 6px solid #b91c1c; }
details.finding.severity-high     { border-left: 6px solid #c2410c; }
details.finding.severity-medium   { border-left: 6px solid #a16207; }
details.finding.severity-low      { border-left: 6px solid #15803d; }
details.finding.severity-info     { border-left: 6px solid #0e7490; }
details.finding summary {
  padding: 1.25rem 1.5rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9375rem;
  color: #0f172a;
  list-style: none;
  display: block;
  line-height: 1.5;
  transition: background 0.15s;
}
details.finding summary:hover { background: #f8fafc; }
details.finding summary::-webkit-details-marker { display: none; }
details.finding summary::before {
  content: "▼";
  font-size: 0.5rem;
  color: #94a3b8;
  margin-right: 0.5rem;
  vertical-align: 0.2em;
  transition: transform 0.2s;
  display: inline-block;
}
details.finding[open] summary::before { transform: rotate(-180deg); vertical-align: 0.15em; }
details.finding[open] summary {
  border-bottom: 1px solid #e2e8f0;
  background: #fafbfc;
  padding-bottom: 1.25rem;
}
details.finding summary .severity-badge {
  margin-right: 0.5rem;
}
details.finding summary .resource-id {
  margin-right: 0.35rem;
}
details.finding summary .summary-msg {
  display: block;
  margin-top: 0.5rem;
  padding-left: 1.25rem;
  color: #475569;
  font-size: 0.9rem;
  font-weight: 400;
  line-height: 1.5;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: normal;
}
details.finding .severity-badge {
  display: inline-block;
  padding: 0.3em 0.65em;
  border-radius: 8px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
details.finding .severity-badge.severity-critical { background: #fef2f2; color: #b91c1c; }
details.finding .severity-badge.severity-high     { background: #fff7ed; color: #c2410c; }
details.finding .severity-badge.severity-medium   { background: #fefce8; color: #a16207; }
details.finding .severity-badge.severity-low      { background: #f0fdf4; color: #15803d; }
details.finding .severity-badge.severity-info     { background: #ecfeff; color: #0e7490; }
details.finding > .finding-inner {
  padding: 1.5rem 1.75rem;
  background: #fff;
}
details.finding .finding-meta {
  list-style: none;
  padding: 0.75rem 1rem;
  margin: 0 0 1.25rem 0;
  font-size: 0.875rem;
  color: #475569;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}
details.finding .finding-meta li { margin: 0.4rem 0; }
details.finding .finding-meta li:first-child { margin-top: 0; }
details.finding .finding-meta li:last-child { margin-bottom: 0; }
details.finding .finding-meta code { font-size: 0.85em; }
details.finding h4 {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
  margin: 1.5rem 0 0.5rem 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
details.finding h4:first-of-type { margin-top: 0; }
details.finding .finding-body {
  margin: 0.5rem 0 0 0;
  padding: 1rem 1.1rem;
  background: #fafbfc;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}
details.finding .finding-body + h4 { margin-top: 1.25rem; }
details.finding .finding-body p { margin: 0.5rem 0; }
details.finding .finding-body p:first-child { margin-top: 0; }
details.finding .finding-body ul { margin: 0.5rem 0; padding-left: 1.35rem; }
details.finding .finding-body li { margin: 0.3rem 0; }
details.finding ul:not(.finding-meta) { margin: 0.5rem 0; padding-left: 1.35rem; }
details.finding li { margin: 0.3rem 0; }
details.finding p { margin: 0.5rem 0; }
code {
  background: #f1f5f9;
  padding: 0.2em 0.5em;
  border-radius: 6px;
  font-size: 0.875em;
  color: #0f172a;
  border: 1px solid #e2e8f0;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 1.25rem 1.5rem;
  border-radius: 10px;
  overflow-x: auto;
  margin: 0.75rem 0;
  font-size: 0.8rem;
  line-height: 1.55;
  border: 1px solid #1e293b;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
}
pre code { background: none; padding: 0; color: inherit; border: none; }
hr { border: 0; border-top: 1px solid #e2e8f0; margin: 2rem 0; }
a { color: #0284c7; text-decoration: none; font-weight: 500; }
a:hover { text-decoration: underline; }
strong { font-weight: 600; color: #0f172a; }
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
        if "severity-" in open_rest:
            return match.group(0)
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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap" rel="stylesheet">
  <style>
{PAGE_CSS}
  </style>
</head>
<body>
<div class="report-header">
{html_body}
</div>
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
