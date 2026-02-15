# Driftguard AI

Infrastructure drift detection and policy enforcement with OPA Rego rules and RAG-backed policy explanations.

## Structure

```
driftguard-ai/
├── infra/              # Sample Terraform to scan
├── policies/           # OPA Rego rules
├── docs/               # Policy explanations (RAG corpus)
├── scripts/            # Python logic
├── reports/            # Generated outputs
├── .github/
│   └── workflows/      # CI/CD workflows
└── README.md
```

## Quick start

1. Add Terraform in `infra/` to scan.
2. Define policies in `policies/` (OPA Rego).
3. Add policy docs in `docs/` for RAG.
4. Run scripts in `scripts/` for scanning and reporting.
5. Check `reports/` for generated outputs.
