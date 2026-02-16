# Policies — OPA/Conftest Rego rules

Rego policies run against Terraform **plan JSON** (`terraform show -json tfplan`). Use [Conftest](https://www.conftest.dev/) to evaluate them.

## Rules (in `rego/`)

| Severity | Rule | Description |
|----------|------|-------------|
| **deny** | Security group open SSH/RDP | Any `aws_security_group` with an ingress rule from `0.0.0.0/0` on port 22 (SSH) or 3389 (RDP). |
| **warn** | Security group open HTTP/HTTPS | Any `aws_security_group` with `0.0.0.0/0` on port 80 or 443; consider WAF. |
| **warn** | S3 missing encryption | Any `aws_s3_bucket` without `server_side_encryption_configuration`. |
| **warn** | S3 no public access block | Any `aws_s3_bucket` without an `aws_s3_bucket_public_access_block`. |
| **warn** | RDS storage not encrypted | Any `aws_db_instance` with `storage_encrypted` disabled or unset. |

## Run Conftest

From the **repo root** (so paths line up):

```bash
# Install Conftest (e.g. locally)
brew install conftest

# Generate plan JSON first (from infra/)
cd infra && terraform init && terraform plan -out=tfplan && terraform show -json tfplan > tfplan.json && cd ..

# Run policies against the plan
conftest test infra/tfplan.json -p policies/rego
```

Or against the sample snippet (for CI without Terraform):

```bash
conftest test policies/examples/sample_plan.json -p policies/rego
```

- **Failures** = at least one `deny` or (with default policy) `warn` triggers; Conftest exits non-zero.
- Use `--no-fail` to see results without exiting non-zero on warnings.

## Input format

Input is the Terraform plan JSON. Policies read:

- `input.resource_changes[]` — each planned resource change
- `change.after` — planned resource attributes (e.g. `ingress`, `server_side_encryption_configuration`)

See `policies/examples/` for a minimal JSON snippet.
