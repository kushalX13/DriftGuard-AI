#!/usr/bin/env bash
# One-command demo: use a sample plan, run the pipeline, open the report.
# Usage: ./demo.sh   (or: make demo)
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"
if [ -d .venv ] && [ -x .venv/bin/python ]; then
  PYTHON=".venv/bin/python"
fi

echo "→ Using sample plan (no Terraform or AWS needed)..."
"$PYTHON" -m scripts.cli plan --tf-dir infra -o infra/tfplan.json \
  --fallback-sample policies/examples/sample_plan.json --sample-only

echo "→ Running DriftGuard (policy → explain → report)..."
"$PYTHON" -m scripts.cli run --plan infra/tfplan.json --fail-on none

echo "→ Converting report to HTML..."
"$PYTHON" -m scripts.md_to_html reports/report.md .pages/demo.html

echo "Done. Report: reports/report.md and .pages/demo.html"
if command -v open >/dev/null 2>&1; then
  open .pages/demo.html
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open .pages/demo.html
fi
