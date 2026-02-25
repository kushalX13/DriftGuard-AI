"""FastAPI server: POST plan JSON → run policy + explain + report → return HTML. For live-run demo and API use."""

import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "policies" / "rego"


def run_pipeline(plan_json: dict) -> tuple[str, dict]:
    """Run policy → explain → report on plan JSON. Returns (report_html, summary)."""
    from scripts.policy_runner import run as policy_run
    from scripts.explain import run as explain_run
    from scripts.report import build_markdown
    from scripts.schemas import ExplanationsReport
    from scripts import md_to_html

    with tempfile.TemporaryDirectory(prefix="driftguard_") as tmp:
        tmp = Path(tmp)
        plan_path = tmp / "tfplan.json"
        findings_path = tmp / "findings.json"
        explanations_path = tmp / "explanations.json"

        plan_path.write_text(json.dumps(plan_json), encoding="utf-8")
        policy_run(plan_path, POLICY_PATH, findings_path)
        explain_run(findings_path, explanations_path)

        report = ExplanationsReport.model_validate_json(explanations_path.read_text(encoding="utf-8"))
        data = report.model_dump()
        summary = data.get("summary") or {}
        md = build_markdown(data, risk_scores_by_key={})
        report_html = md_to_html.markdown_to_html_string(md)
        return report_html, summary


app = FastAPI(
    title="DriftGuard API",
    description="POST Terraform plan JSON; get a policy report (HTML or JSON).",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "message": "DriftGuard API",
        "docs": "/docs",
        "run": "POST /api/run with Terraform plan JSON (terraform show -json tfplan) in the request body.",
    }


@app.post("/api/run")
def api_run(body: dict) -> JSONResponse:
    """Accept Terraform plan JSON (as sent in request body). Run policy + explain + report; return report HTML and summary."""
    try:
        report_html, summary = run_pipeline(body)
        total = sum(summary.get(k, 0) for k in ("critical", "high", "medium", "low", "info"))
        return JSONResponse(
            content={
                "report_html": report_html,
                "summary": summary,
                "findings_count": total,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


SAMPLE_PLAN_JSON = (
    '{"format_version":"1.0","resource_changes":[{"address":"aws_s3_bucket.bad_bucket","mode":"managed",'
    '"type":"aws_s3_bucket","name":"bad_bucket","change":{"actions":["create"],"before":null,"after":{"bucket":"my-open-bucket"}}},'
    '{"address":"aws_security_group.open_ingress","mode":"managed","type":"aws_security_group","name":"open_ingress",'
    '"change":{"actions":["create"],"before":null,"after":{"name":"allow-all-in","description":"Allow all inbound",'
    '"ingress":[{"from_port":0,"to_port":65535,"protocol":"tcp","cidr_blocks":["0.0.0.0/0"]}]}}},'
    '{"address":"aws_db_instance.example","mode":"managed","type":"aws_db_instance","name":"example",'
    '"change":{"actions":["create"],"before":null,"after":{"identifier":"example-db","engine":"postgres","allocated_storage":20,"instance_class":"db.t3.micro"}}}]}'
)


@app.get("/live", response_class=HTMLResponse)
def live() -> str:
    """Live run UI: paste plan JSON, click Run, see report (calls /api/run)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DriftGuard — Live run</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: "DM Sans", sans-serif; margin: 0; padding: 2rem; background: #f1f5f9; color: #1e293b; }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.5rem 0; }}
    .sub {{ color: #64748b; margin-bottom: 1rem; font-size: 0.9rem; }}
    textarea {{ width: 100%; height: 140px; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px; font-family: ui-monospace, monospace; font-size: 0.8rem; }}
    button {{ background: #0284c7; color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 0.5rem; }}
    button:hover {{ background: #0369a1; }}
    button:disabled {{ opacity: 0.6; cursor: not-allowed; }}
    #error {{ color: #dc2626; margin-top: 0.5rem; }}
    #result {{ margin-top: 1.5rem; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #fff; min-height: 400px; }}
    #result iframe {{ width: 100%; height: 80vh; min-height: 500px; border: none; }}
  </style>
</head>
<body>
  <h1>Live run</h1>
  <p class="sub">Paste Terraform plan JSON (from <code>terraform show -json tfplan</code>) and run. The report is generated from your input.</p>
  <textarea id="plan" placeholder="Paste plan JSON here...">{SAMPLE_PLAN_JSON}</textarea>
  <br>
  <button type="button" id="run">Run</button>
  <div id="error"></div>
  <div id="result"></div>
  <script>
    document.getElementById("run").addEventListener("click", async () => {{
      const ta = document.getElementById("plan");
      const err = document.getElementById("error");
      const res = document.getElementById("result");
      err.textContent = "";
      res.innerHTML = "";
      let plan;
      try {{
        plan = JSON.parse(ta.value);
      }} catch (e) {{
        err.textContent = "Invalid JSON: " + e.message;
        return;
      }}
      const btn = document.getElementById("run");
      btn.disabled = true;
      try {{
        const r = await fetch("/api/run", {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(plan) }});
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || r.statusText);
        const iframe = document.createElement("iframe");
        iframe.srcdoc = data.report_html;
        res.appendChild(iframe);
      }} catch (e) {{
        err.textContent = e.message;
      }} finally {{
        btn.disabled = false;
      }}
    }});
  </script>
</body>
</html>"""


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
