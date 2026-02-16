"""Convert report.md to a self-contained HTML file for GitHub Pages."""

from pathlib import Path

import markdown

# Minimal CSS for a clean, readable report (works with GitHub-flavored markdown output)
PAGE_CSS = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
  color: #24292f;
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  background: #f6f8fa;
}
h1 { font-size: 1.75rem; margin-top: 0; color: #1f2328; }
h2 { font-size: 1.25rem; margin-top: 1.5rem; border-bottom: 1px solid #d0d7de; padding-bottom: 0.25rem; }
h3, h4 { font-size: 1rem; margin-top: 1rem; }
p { margin: 0.5rem 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #d0d7de; }
th { background: #f6f8fa; font-weight: 600; }
tr:last-child td { border-bottom: 0; }
details { margin: 0.75rem 0; background: #fff; border-radius: 6px; border: 1px solid #d0d7de; overflow: hidden; }
summary { padding: 0.6rem 0.75rem; cursor: pointer; font-weight: 500; }
details[open] summary { border-bottom: 1px solid #d0d7de; }
details > div { padding: 0.75rem 1rem; }
code { background: #f6f8fa; padding: 0.2em 0.4em; border-radius: 4px; font-size: 0.9em; }
pre { background: #f6f8fa; padding: 1rem; border-radius: 6px; overflow-x: auto; }
pre code { padding: 0; background: none; }
ul { margin: 0.5rem 0; padding-left: 1.5rem; }
.meta { color: #656d76; font-size: 0.9rem; margin-bottom: 1rem; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 1.5rem 0; }
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
"""


def convert(md_path: str | Path, out_path: str | Path, title: str = "DriftGuard Policy Report") -> Path:
    """Read markdown file, convert to HTML with template, write to out_path. Returns out_path."""
    md_path = Path(md_path)
    out_path = Path(out_path)
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    raw = md_path.read_text(encoding="utf-8")
    # GitHub-style: tables, fenced code, nl2br optional
    html_body = markdown.markdown(
        raw,
        extensions=["tables", "fenced_code", "nl2br"],
        extension_configs={"tables": {}},
    )

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
