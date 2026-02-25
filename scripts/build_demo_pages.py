"""Build interactive demo: three scenario report HTMLs + picker index for GitHub Pages."""

import shutil
import sys
from pathlib import Path

# Repo paths
ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
POLICY_PATH = ROOT / "policies" / "rego"
EXAMPLES_DIR = ROOT / "policies" / "examples"
PAGES_DIR = ROOT / ".pages"
PLAN_PATH = ROOT / "infra" / "tfplan.json"

SCENARIOS = [
    ("clean", "sample_plan_clean.json", "Compliant Terraform", "No misconfigurations — restricted SG, encrypted RDS, S3 locked down.", "0 findings", "report_clean.html"),
    ("medium", "sample_plan_medium.json", "One mistake: Open SSH", "Security group allows 0.0.0.0/0 on port 22 (SSH).", "1 critical finding", "report_medium.html"),
    ("full", "sample_plan.json", "Multiple issues", "Open SSH/RDP, unencrypted RDS, S3 without encryption or public access block.", "5 findings", "report_full.html"),
]


def build_one(scenario_id: str, sample_name: str, out_html: str) -> None:
    """Run pipeline for one sample plan and write report to .pages/<out_html>."""
    plan_src = EXAMPLES_DIR / sample_name
    if not plan_src.exists():
        raise FileNotFoundError(f"Sample plan not found: {plan_src}")

    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(plan_src, PLAN_PATH)

    from scripts.policy_runner import run as policy_run
    from scripts.explain import run as explain_run
    from scripts.report import run as report_run
    from scripts import md_to_html

    findings_path = REPORTS_DIR / "findings.json"
    explanations_path = REPORTS_DIR / "explanations.json"
    report_md = REPORTS_DIR / "report.md"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    policy_run(PLAN_PATH, POLICY_PATH, findings_path)
    explain_run(findings_path, explanations_path)
    report_run(explanations_path, report_md, findings_path, risk_scores_path=None, include_risk_scores=False)
    md_to_html.convert(report_md, PAGES_DIR / out_html)
    print(f"  Built {out_html}")


def write_picker_index() -> None:
    """Write .pages/index.html: landing with four entry points + scenario picker."""
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    index = PAGES_DIR / "index.html"

    cards_html = ""
    for _id, _sample, title, desc, badge, report_file in SCENARIOS:
        cards_html += f"""
        <div class="card" data-report="{report_file}">
          <div class="card-badge">{badge}</div>
          <h3>{title}</h3>
          <p>{desc}</p>
          <button type="button" class="btn" aria-label="Show report for {title}">Show report</button>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DriftGuard — Try it</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: "DM Sans", sans-serif; margin: 0; padding: 0; background: #f1f5f9; color: #1e293b; line-height: 1.5; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }}
    h1 {{ font-size: 1.75rem; margin: 0 0 0.5rem 0; color: #0f172a; }}
    .subtitle {{ color: #64748b; margin: 0 0 1.5rem 0; font-size: 1rem; }}
    .entry-points {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2.5rem; }}
    .entry {{ background: #fff; border-radius: 12px; padding: 1.1rem; border: 1px solid #e2e8f0; text-align: center; transition: box-shadow 0.2s; }}
    .entry:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,.08); }}
    .entry a {{ color: #0284c7; font-weight: 500; text-decoration: none; display: block; }}
    .entry a:hover {{ text-decoration: underline; }}
    .entry .label {{ font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }}
    h2 {{ font-size: 1.15rem; margin: 1.5rem 0 1rem 0; color: #0f172a; }}
    .scenarios {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }}
    .card {{ background: #fff; border-radius: 14px; padding: 1.35rem; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,.05); transition: box-shadow 0.2s, border-color 0.2s; }}
    .card:hover {{ box-shadow: 0 8px 20px rgba(0,0,0,.08); border-color: #cbd5e1; }}
    .card-badge {{ display: inline-block; font-size: 0.75rem; font-weight: 600; color: #475569; background: #f1f5f9; padding: 0.25em 0.6em; border-radius: 6px; margin-bottom: 0.75rem; }}
    .card h3 {{ font-size: 1.1rem; margin: 0 0 0.5rem 0; color: #0f172a; }}
    .card p {{ font-size: 0.9rem; color: #64748b; margin: 0 0 1rem 0; }}
    .btn {{ background: #0284c7; color: #fff; border: none; padding: 0.6rem 1.1rem; border-radius: 8px; font-size: 0.9rem; font-weight: 500; cursor: pointer; font-family: inherit; }}
    .btn:hover {{ background: #0369a1; }}
    .report-container {{ display: none; margin-top: 1.5rem; }}
    .report-container.visible {{ display: block; }}
    .report-container iframe {{ width: 100%; height: 80vh; min-height: 500px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }}
    .back {{ margin-bottom: 1rem; }}
    .back button {{ background: #64748b; color: #fff; border: none; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.875rem; cursor: pointer; font-family: inherit; }}
    .back button:hover {{ background: #475569; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>DriftGuard</h1>
    <p class="subtitle">Catch Terraform misconfigs before apply. Try it four ways:</p>
    <div class="entry-points">
      <div class="entry"><a href="#scenarios">Try in browser</a><div class="label">Pre-built scenarios below</div></div>
      <div class="entry"><a href="api.html#run-in-github">Run in GitHub</a><div class="label">Template · Codespaces · make demo</div></div>
      <div class="entry"><a href="live-run.html">Live run</a><div class="label">Paste plan → real report</div></div>
      <div class="entry"><a href="api.html">API</a><div class="label">POST plan JSON → report</div></div>
    </div>
    <h2 id="scenarios">Pre-built scenarios</h2>
    <p class="subtitle">Click a scenario to see the report DriftGuard would produce.</p>
    <div class="scenarios">
      {cards_html}
    </div>
    <div class="report-container" id="report-container">
      <div class="back"><button type="button" id="back-btn">← Back to scenarios</button></div>
      <iframe id="report-frame" title="DriftGuard report"></iframe>
    </div>
  </div>
  <script>
    document.querySelectorAll(".card .btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const card = btn.closest(".card");
        const report = card.getAttribute("data-report");
        const frame = document.getElementById("report-frame");
        const container = document.getElementById("report-container");
        frame.src = report;
        container.classList.add("visible");
      }});
    }});
    document.getElementById("back-btn").addEventListener("click", () => {{
      document.getElementById("report-frame").src = "";
      document.getElementById("report-container").classList.remove("visible");
    }});
  </script>
</body>
</html>"""
    index.write_text(html, encoding="utf-8")
    print("  Built index.html (landing + picker)")


def write_static_info_pages() -> None:
    """Write live-run.html and api.html (how to use Live run and API)."""
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    style = "body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1.5rem;line-height:1.6;} code{background:#f1f5f9;padding:0.2em 0.4em;border-radius:4px;} a{color:#0284c7;}"

    live_run = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Live run</title><style>{style}</style></head><body>
<h1>Live run</h1>
<p>Paste Terraform plan JSON and get a report generated from <em>your</em> input (not pre-built).</p>
<ol>
  <li>Install the API extra: <code>pip install '.[api]'</code></li>
  <li>Install Conftest (e.g. <code>brew install conftest</code>)</li>
  <li>Start the server: <code>python -m scripts.cli api</code> or <code>make api</code></li>
  <li>Open <a href="http://localhost:8000/live">http://localhost:8000/live</a></li>
  <li>Paste plan JSON (or use the sample), click Run</li>
</ol>
<p><a href="index.html">← Back</a></p>
</body></html>"""
    (PAGES_DIR / "live-run.html").write_text(live_run, encoding="utf-8")

    api_page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>API</title><style>{style}</style></head><body>
<h1>API</h1>
<p>POST Terraform plan JSON to <code>/api/run</code>; get back report HTML and summary.</p>
<ol>
  <li>Start the server: <code>python -m scripts.cli api</code> (requires <code>pip install '.[api]'</code> and Conftest)</li>
  <li>Open <a href="http://localhost:8000/docs">http://localhost:8000/docs</a> for Swagger UI</li>
  <li>Or: <code>curl -X POST http://localhost:8000/api/run -H "Content-Type: application/json" -d @infra/tfplan.json</code></li>
</ol>
<h2 id="run-in-github">Run in GitHub</h2>
<p>Use this repo as a template or open in <strong>GitHub Codespaces</strong>. Then run <code>make demo</code> (after <code>make install</code> and installing Conftest). Edit <code>infra/*.tf</code>, run <code>terraform plan</code>, then DriftGuard to see the report for your plan.</p>
<p><a href="index.html">← Back</a></p>
</body></html>"""
    (PAGES_DIR / "api.html").write_text(api_page, encoding="utf-8")
    print("  Built live-run.html, api.html")


def main() -> None:
    print("Building demo pages...")
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for scenario_id, sample_name, _title, _desc, _badge, out_html in SCENARIOS:
        build_one(scenario_id, sample_name, out_html)
    write_picker_index()
    write_static_info_pages()
    print("Done. Open .pages/index.html in a browser.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
