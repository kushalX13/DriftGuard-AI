# Policy examples

Sample Terraform plan JSONs (same shape as `terraform show -json`). Use them to test Conftest or to drive the demo so the report isn’t always the same.

| File | Purpose | Findings |
|------|---------|----------|
| **`sample_plan_clean.json`** | Compliant resources (restricted SG, encrypted RDS, S3 encrypted + public access block) | **0** — report shows “No policy issues found” |
| **`sample_plan_medium.json`** | One misconfiguration (open SSH) | **1** critical |
| **`sample_plan.json`** | Multiple misconfigurations | **5** (1 critical, 4 warn) |

The GitHub Pages workflow picks one of these per run (by `run_id % 3`), so each deploy can show a passing report, one finding, or the full set — like fixing issues and re-running in the real world.

**Test Conftest without Terraform:**

```bash
conftest test policies/examples/sample_plan.json -p policies/rego
conftest test policies/examples/sample_plan_clean.json -p policies/rego   # 0 findings
conftest test policies/examples/sample_plan_medium.json -p policies/rego  # 1 deny
```
