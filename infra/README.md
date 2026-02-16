# Infra — sample Terraform for DriftGuard

Tiny AWS Terraform project with **deliberately insecure** resources for policy scanning. Safe to run without applying (no credentials required for init; plan may need AWS env vars for provider init).

## Insecure resources in `main.tf`

- **S3 bucket** `my-open-bucket` — no encryption, no public access block.
- **Security group** `allow-all-in` — TCP 0–65535 from `0.0.0.0/0`.

## Produce `tfplan.json` (reproducible artifact)

From this directory (`infra/`):

```bash
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
```

- `tfplan` — binary plan file (ignored by git).
- `tfplan.json` — JSON plan for DriftGuard (ignored by git; generate locally or in CI).

Use `tfplan.json` as input to the `plan` / `policy` pipeline. No `terraform apply` is needed.
