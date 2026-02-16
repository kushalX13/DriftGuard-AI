# RDS instance: storage encryption disabled

## What this means

The RDS DB instance does not have storage encryption enabled. Data at rest in the underlying EBS volumes and snapshots is stored unencrypted.

## Why it matters

- Compliance frameworks (PCI-DSS, HIPAA, etc.) typically require encryption of database storage.
- Unencrypted snapshots or volume copies can expose sensitive data.
- Encryption at rest is a baseline control for production databases.

## How to fix

Set `storage_encrypted = true` on the RDS instance. This cannot be changed after creation; to enable encryption on an existing instance you must create a new instance with encryption and migrate.

**Terraform snippet:**

```hcl
resource "aws_db_instance" "example" {
  identifier     = "my-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_encrypted = true

  db_name  = "app"
  username = "admin"
  password = var.db_password
}
```

For MySQL/Postgres you can also reference a KMS key:

```hcl
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn
```

## References

- [AWS RDS encryption at rest](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html)
- [aws_db_instance storage_encrypted](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/db_instance#storage_encrypted)
