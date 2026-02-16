# S3 bucket: missing server-side encryption

## What this means

The S3 bucket has no server-side encryption configuration. Data at rest in the bucket is stored unencrypted by default. Enabling server-side encryption (SSE) ensures objects are encrypted using AWS-managed or customer-managed keys.

## Why it matters

- Unencrypted buckets can expose sensitive data if the bucket is misconfigured, leaked, or compromised.
- Many compliance standards (e.g. PCI-DSS, HIPAA) require encryption of data at rest.
- Enabling SSE-S3 or SSE-KMS is a low-effort, high-impact hardening step.

## How to fix

Add a `server_side_encryption_configuration` block to the bucket, or use the separate `aws_s3_bucket_server_side_encryption_configuration` resource.

**Terraform snippet (inline on bucket):**

```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
  bucket = aws_s3_bucket.example.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}
```

**Terraform snippet (older provider – rule block on bucket):**

```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
      bucket_key_enabled = true
    }
  }
}
```

Use `AES256` for SSE-S3 or `aws:kms` (and optionally `kms_master_key_id`) for SSE-KMS.

## References

- [AWS S3 default encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html)
- [aws_s3_bucket_server_side_encryption_configuration](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration)
