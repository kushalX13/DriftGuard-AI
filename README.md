# DriftGuard

**Catch Terraform misconfigs before apply.** DriftGuard runs OPA/Conftest policies on your plan JSON, normalizes findings, attaches remediation docs (no LLM), and emits a PR-ready report. One command locally or in CI. **Policy engine is authoritative; ML risk scoring is optional and experimental.**

**Built with:** Python 3.11, FastAPI, OPA/Rego (Conftest), Terraform, optional MLflow, GitHub Actions, GitHub Pages.

---

## Architecture

```
  infra/*.tf  ──►  terraform plan -out=tfplan
                          │
                          ▼
              terraform show -json tfplan  ──►  tfplan.json
                          │
                          ▼
              Conftest (OPA Rego)  ──►  findings.json  (severity, resource, rule id)
                          │
                          ▼
              Doc retrieval (docs/*.md)  ──►  explanations.json  (why it matters, how to fix)
                          │
                          ▼
              Report generator  ──►  report.md  (summary table + collapsible findings)
```

**Policies today:** deny security groups with 0.0.0.0/0 on SSH (22) or RDP (3389); warn S3 buckets without server-side encryption or without public access block; warn security groups with 0.0.0.0/0 on HTTP (80) or HTTPS (443); warn RDS instances without storage encryption. Extend by adding Rego in `policies/rego/` and docs in `docs/`.

---

## Ways to try DriftGuard

| Way | What you do | Best for |
|-----|-------------|----------|
| **One-command demo** | `make demo` or `./demo.sh` | Run the full pipeline locally and open the report. |
| **Run in GitHub** | Use template → open in Codespaces → edit Terraform → `make demo` | Real repo, real pipeline; no install on your machine. |
| **Live run** | Start API (`make api`), open http://localhost:8000/live — sample plan is pre-loaded; paste your own or use **Load sample 2** → Run | See the report generated from *your* plan (real run). |
| **API** | `POST /api/run` with Terraform plan JSON → report HTML/JSON; `GET /api/sample-plan` (optional `?variant=2`) for sample plans | Integrate into your own app or CI. |

---

## Try it locally

No AWS credentials (and optionally no Terraform) needed: one-command demo.

```bash
# Install (once)
make install
# Conftest (once, for run): brew install conftest

# 1. Produce plan JSON (no manual Terraform steps)
#    With Terraform installed: uses sample if plan fails (e.g. no AWS creds)
python -m scripts.cli plan --tf-dir infra --out infra/tfplan.json --fallback-sample policies/examples/sample_plan.json

#    Without Terraform: skip Terraform and copy sample
python -m scripts.cli plan --tf-dir infra --out infra/tfplan.json --fallback-sample policies/examples/sample_plan.json --sample-only

# 2. Generate reports (policy → explain → report; policy-only by default)
python -m scripts.cli run --plan infra/tfplan.json
# Optional: add ML severity/risk scoring
python -m scripts.cli run --plan infra/tfplan.json --enable-ml
# Optional: humanize explanations with OpenAI (do not put the key in git)
#   pip install '.[llm]'
#   cp .env.example .env   # then edit .env and set OPENAI_API_KEY=sk-...
#   python -m scripts.cli run --plan infra/tfplan.json --use-llm
```

Then open `reports/report.md`. Or run **one command**: `make demo` (or `./demo.sh`) to use a sample plan, run the pipeline, and open the HTML report.

**API & live run:** Run `make install` then `make api` (or `pip install '.[api]'` and `python -m scripts.cli api`). Open http://localhost:8000/live — a sample plan is pre-loaded; click Run or paste your own plan JSON. API docs: http://localhost:8000/docs.

**API key (for `--use-llm`):** put it in a **`.env`** file (already in `.gitignore`). Copy `.env.example` to `.env`, add your key there; never commit `.env` or the key to git. With real Terraform and creds, drop `--fallback-sample` (and `--sample-only`) and run the same `plan` then `run` commands.

**Optional step-by-step:**

```bash
python -m scripts.cli plan --tf-dir infra -o infra/tfplan.json [--fallback-sample policies/examples/sample_plan.json]
python -m scripts.cli policy -p infra/tfplan.json -o reports/findings.json
python -m scripts.cli explain -f reports/findings.json -o reports/explanations.json
python -m scripts.cli report -e reports/explanations.json -o reports/report.md
```

### Run in GitHub (template + Codespaces)

1. **Use this template** (if the repo is set as a template) or clone the repo.
2. **Open in GitHub Codespaces** (Code → Codespaces → Create codespace). No local install.
3. In the terminal: `make install` (or `pip install -e ".[dev]"`), install Conftest (`brew install conftest` or [install script](https://www.conftest.dev/install/)), then `make demo`.
4. Edit `infra/*.tf` (e.g. add a security group with `0.0.0.0/0`), run `terraform plan -out=tfplan` and `terraform show -json tfplan > infra/tfplan.json`, then `python -m scripts.cli run --plan infra/tfplan.json` to see the report for *your* plan.

---

## CI behavior

On every **pull request** (to `main` or `master`):

1. **Checkout** → **Python 3.11** → **Conftest** (pinned) → **Terraform** (setup-terraform).
2. **Terraform:** `fmt -check`, `init -backend=false`, `validate`. Then `plan -out=tfplan`; if that fails (e.g. no AWS creds in CI), the workflow uses `policies/examples/sample_plan.json` so the rest still runs.
3. **ML (opt-in):** The pipeline is **policy-only by default**. Use `--enable-ml` to run the severity model when `ml/models/severity_model.pkl` exists; then the report includes predicted severity and risk scores.
4. **DriftGuard pipeline:** `python -m scripts.cli run --plan infra/tfplan.json` → produces `reports/findings.json`, `reports/explanations.json`, `reports/report.md`. With `--enable-ml`: also `reports/risk_scores.json` and ML block in the report.
5. **Artifact:** `reports/` is uploaded as `driftguard-reports` (7-day retention). The report is also printed in the job log.
6. **PR comment:** If the PR is from the **same repo** (not a fork), the workflow posts or updates a comment with the report body. Fork PRs skip the comment but still get the artifact and logs.

No AWS credentials or secrets required for CI; the “plan fails → sample fallback” keeps the pipeline green and demo-friendly.

**ML scoring in CI:** To have the report show predicted severity and risk scores in CI, either (1) check in a baseline model: `python -m scripts.build_baseline_model` then commit `ml/models/`, or (2) run the **Train model** workflow (Actions → Train model → Run workflow) once; CI will use the uploaded model artifact when present.

---

## Demo report (GitHub Pages)

On **push to main** (or **master**), the **Pages** workflow builds an **interactive demo** and deploys it to GitHub Pages. Visitors can choose a scenario (compliant Terraform, one mistake, or multiple issues) and see the report that DriftGuard would produce — “I did this, and this is what it found.”

**`https://<owner>.github.io/<repo>/`**

(e.g. `https://kushalx13.github.io/DriftGuard-AI/`)

**One-time setup:** GitHub Pages must be enabled first. On the free plan, **Pages only works for public repos**: make the repo public (Settings → General → Change repository visibility), then go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**. After the first push to main, the workflow publishes the demo; the root URL serves the interactive picker — choose a scenario to see that report. (To keep the repo private, skip Pages—the PR workflow still uploads the report as an artifact and comments on PRs.)

**Deploy failed with 404?** Enable Pages: ensure the repo is public (or you have Enterprise for private Pages), then set **Source** to **GitHub Actions** under Settings → Pages.

---

## Sample report output

What `reports/report.md` looks like (summary + one finding expanded):

```markdown
# DriftGuard Policy Report

*Generated: 2025-02-15 14:30:00 UTC*

---

## Summary

| Severity | Count |
|---------|-------|
| Critical | 1 |
| High | 1 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |

---

## Findings

<details>
<summary>**CRITICAL** — `aws_security_group.open_ingress` — Security group allows 0.0.0.0/0 on SSH (22) or RDP (3389): high risk</summary>

- **Resource:** `aws_security_group.open_ingress`
- **Rule:** `DG-SG-OPEN-SSH`
- **Message:** Security group allows 0.0.0.0/0 on SSH (22) or RDP (3389): high risk

#### Why it matters

SSH (22) and RDP (3389) are high-value targets for brute-force and credential stuffing. Exposing them to the world greatly increases compromise risk. Compliance frameworks (e.g. CIS, PCI-DSS) typically require restricting administrative access to known IP ranges.

#### How to fix

Restrict ingress to a known CIDR (e.g. VPN or bastion). Add an ingress block with `cidr_blocks = ["10.0.0.0/8"]` (or your VPN range) instead of `0.0.0.0/0`.

#### References

- [sg_open_ssh](docs/sg_open_ssh.md)
</details>

<details>
<summary>**HIGH** — `aws_s3_bucket.bad_bucket` — S3 bucket has no server_side_encryption_configuration</summary>
...
</details>
```

This is the same markdown used in CI for the PR comment and in the uploaded artifact.

---

## Repo structure

```
driftguard-ai/
├── infra/                 # Sample Terraform (AWS; deliberately insecure for demo)
├── policies/
│   ├── rego/              # OPA/Conftest rules (terraform plan JSON)
│   └── examples/          # sample_plan.json (schema-aligned with terraform show -json)
├── docs/                  # Remediation docs (What / Why / How to fix / References)
├── scripts/               # Python: cli, plan_runner, policy_runner, explain, report, api_server, md_to_html, build_demo_pages, build_baseline_model
├── reports/               # Generated: findings.json, explanations.json, report.md
├── .github/workflows/     # driftguard.yml (PR → plan/fallback → run → artifact + comment)
├── Makefile               # install, fmt, lint, test, run-sample
└── README.md
```

---

## Severity classifier (ML lifecycle)

The pipeline optionally runs a severity classifier (see **ML scoring in CI**). We treat class imbalance explicitly:

- **Baseline (no balancing):** Original synthetic data and default classifier → **macro-F1 ~0.70**, class 3 (LOW) recall **0** (minority class ignored).
- **Improved run:** `class_weight="balanced"`, synthetic data rebalanced with more class 3 (LOW), new run logged to MLflow.
  - **Improved macro-F1: 0.90** (reproduce with `python -m scripts.cli synth` then `python -m scripts.cli train`).
  - **Class 3 (LOW) recall: 0 → 0.97** (minority class now learned).

That’s the full ML lifecycle story: baseline → fix imbalance → log improved run → report better metrics.

---

## Development

```bash
make install          # .venv + pip install -e ".[dev]"
make run-sample       # python -m scripts.cli --help
make fmt && make lint
make test
```

CLI: `plan`, `policy`, `explain`, `report`, `run`, `api`, `synth`, `train`. From repo root: `python -m scripts.cli --help`.

---

## License

MIT.
