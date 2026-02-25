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


@app.get("/api/sample-plan")
def api_sample_plan(variant: int = 1) -> JSONResponse:
    """Return sample Terraform plan JSON for the Live run UI. variant=1 (default) or 2."""
    plan = json.loads(SAMPLE_PLAN_JSON_2 if variant == 2 else SAMPLE_PLAN_JSON)
    return JSONResponse(content=plan)


SAMPLE_PLAN_JSON = (
    '{"format_version":"1.0","resource_changes":[{"address":"aws_s3_bucket.bad_bucket","mode":"managed",'
    '"type":"aws_s3_bucket","name":"bad_bucket","change":{"actions":["create"],"before":null,"after":{"bucket":"my-open-bucket"}}},'
    '{"address":"aws_security_group.open_ingress","mode":"managed","type":"aws_security_group","name":"open_ingress",'
    '"change":{"actions":["create"],"before":null,"after":{"name":"allow-all-in","description":"Allow all inbound",'
    '"ingress":[{"from_port":0,"to_port":65535,"protocol":"tcp","cidr_blocks":["0.0.0.0/0"]}]}}},'
    '{"address":"aws_db_instance.example","mode":"managed","type":"aws_db_instance","name":"example",'
    '"change":{"actions":["create"],"before":null,"after":{"identifier":"example-db","engine":"postgres","allocated_storage":20,"instance_class":"db.t3.micro"}}}]}'
)

# Second sample: different resources so you can test "machine finds it" (RDS unencrypted, S3 open, SG SSH open).
SAMPLE_PLAN_JSON_2 = (
    '{"format_version":"1.0","resource_changes":['
    '{"address":"aws_s3_bucket.logs","mode":"managed","type":"aws_s3_bucket","name":"logs",'
    '"change":{"actions":["create"],"before":null,"after":{"bucket":"company-logs-bucket"}}},'
    '{"address":"aws_security_group.bastion","mode":"managed","type":"aws_security_group","name":"bastion",'
    '"change":{"actions":["create"],"before":null,"after":{"name":"bastion-sg","description":"SSH from internet",'
    '"ingress":[{"from_port":22,"to_port":22,"protocol":"tcp","cidr_blocks":["0.0.0.0/0"]}]}}},'
    '{"address":"aws_db_instance.analytics","mode":"managed","type":"aws_db_instance","name":"analytics",'
    '"change":{"actions":["create"],"before":null,"after":{"identifier":"analytics-db","engine":"postgres",'
    '"allocated_storage":100,"instance_class":"db.t3.medium"}}}]}'
)


def _live_textarea_initial() -> str:
    """Formatted sample plan safe inside <textarea> (must not contain </textarea>)."""
    s = json.dumps(json.loads(SAMPLE_PLAN_JSON), indent=2)
    return s.replace("</", "<\\/")  # avoid closing script/textarea if ever present


@app.get("/live", response_class=HTMLResponse)
def live() -> str:
    """Live run UI: sample JSON is in the HTML so it shows and Run works with no JS dependency."""
    initial_json = _live_textarea_initial()
    return (
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DriftGuard — Live run</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body { font-family: "DM Sans", sans-serif; margin: 0; padding: 2rem; background: #f1f5f9; color: #1e293b; }
    h1 { font-size: 1.5rem; margin: 0 0 0.5rem 0; }
    .sub { color: #64748b; margin-bottom: 1rem; font-size: 0.9rem; }
    textarea { width: 100%; height: 320px; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px; font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.8rem; line-height: 1.4; resize: vertical; }
    button { background: #0284c7; color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 1rem; cursor: pointer; margin-top: 0.5rem; }
    button:hover { background: #0369a1; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    #error { color: #dc2626; margin-top: 0.5rem; padding: 0.75rem; background: #fef2f2; border-radius: 6px; border: 1px solid #fecaca; }
    #error:empty { display: none; }
    #result { margin-top: 1.5rem; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #fff; min-height: 400px; }
    #result iframe { width: 100%; height: 80vh; min-height: 500px; border: none; }
  </style>
</head>
<body>
  <h1>Live run</h1>
  <p class="sub">Paste Terraform plan JSON (from <code>terraform show -json tfplan</code>) and run. The report is generated from your input.</p>
  <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 0.75rem 1rem; margin-bottom: 1rem; border-radius: 6px; font-size: 0.85rem;">
    <strong>Note:</strong> This is <strong>JSON</strong> format (from <code>terraform show -json</code>), not Terraform HCL. Use colons <code>:</code> not equals <code>=</code>.
  </div>
  <textarea id="plan" placeholder="Paste plan JSON here..." spellcheck="false">"""
        + initial_json
        + """</textarea>
  <br>
  <button type="button" id="run">Run</button>
  <button type="button" id="clear" style="background: #64748b; margin-left: 0.5rem;">Reset to sample</button>
  <button type="button" id="load2" style="background: #64748b; margin-left: 0.5rem;">Load sample 2</button>
  <div id="error"></div>
  <div id="result"></div>
  <script>
document.addEventListener("DOMContentLoaded", function() {
  try {
    var planEl = document.getElementById("plan");
    var errEl = document.getElementById("error");
    var resEl = document.getElementById("result");
    var runBtn = document.getElementById("run");
    var clearBtn = document.getElementById("clear");
    var load2Btn = document.getElementById("load2");
    var samplePlan = null;
    try { samplePlan = JSON.parse(planEl.value || "{}"); } catch (e) {}

    function showError(msg) {
      errEl.textContent = msg;
      errEl.style.display = "block";
      resEl.innerHTML = "<p style=\"padding:1rem;color:#dc2626;background:#fef2f2;border-radius:8px;\">" + String(msg).replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</p>";
    }
    function clearError() {
      errEl.textContent = "";
      errEl.style.display = "";
    }

    clearBtn.addEventListener("click", function() {
      if (samplePlan) planEl.value = JSON.stringify(samplePlan, null, 2);
      clearError();
      resEl.innerHTML = "";
    });

    load2Btn.addEventListener("click", function() {
      load2Btn.disabled = true;
      load2Btn.textContent = "Loading...";
      fetch("/api/sample-plan?variant=2")
        .then(function(r) { return r.json(); })
        .then(function(data) {
          samplePlan = data;
          planEl.value = JSON.stringify(data, null, 2);
          clearError();
          resEl.innerHTML = "";
        })
        .catch(function(e) {
          showError("Could not load sample 2: " + (e.message || e));
        })
        .then(function() {
          load2Btn.disabled = false;
          load2Btn.textContent = "Load sample 2";
        });
    });

    runBtn.addEventListener("click", function() {
      clearError();
      resEl.innerHTML = "<p style=\"padding:1rem;color:#64748b;\">Running...</p>";
      var plan;
      try {
        plan = JSON.parse(planEl.value || "{}");
      } catch (e) {
        resEl.innerHTML = "";
        showError("Invalid JSON: " + (e.message || e));
        return;
      }
      if (!plan.resource_changes) {
        resEl.innerHTML = "";
        showError("Invalid plan: need resource_changes");
        return;
      }
      runBtn.disabled = true;
      runBtn.textContent = "Running...";
      fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan)
      })
        .then(function(r) {
          if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || r.statusText); });
          return r.json();
        })
        .then(function(data) {
          if (!data || !data.report_html) throw new Error("No report in response");
          resEl.innerHTML = "";
          var iframe = document.createElement("iframe");
          iframe.srcdoc = data.report_html;
          iframe.setAttribute("sandbox", "allow-same-origin allow-scripts");
          resEl.appendChild(iframe);
        })
        .catch(function(e) {
          showError("Error: " + (e.message || String(e)));
          resEl.innerHTML = "";
        })
        .then(function() {
          runBtn.disabled = false;
          runBtn.textContent = "Run";
        });
    });
  } catch (e) {
    document.getElementById("error").textContent = "Page error: " + (e.message || String(e));
    document.getElementById("error").style.display = "block";
  }
});
  </script>
</body>
</html>"""
    )


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
