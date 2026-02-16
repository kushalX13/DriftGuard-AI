# Policy examples

- **`sample_plan.json`** — Terraform plan JSON shaped like `terraform show -json` output: `format_version`, `resource_changes[]` with `address`, `mode`, `type`, `name`, `change.after` (and `change.before`). Matches what Rego reads. Triggers multiple rules:
  - **deny**: `aws_security_group.open_ingress` — 0.0.0.0/0 on SSH (22) or RDP (3389).
  - **warn**: same SG — 0.0.0.0/0 on HTTP (80) or HTTPS (443).
  - **warn**: `aws_s3_bucket.bad_bucket` — no encryption, no public access block.
  - **warn**: `aws_db_instance.example` — storage_encrypted not set.

Use it to test Conftest without running Terraform:

```bash
conftest test policies/examples/sample_plan.json -p policies/rego
```

Expected: at least one **deny** and one **warn** (Conftest exits non-zero).
