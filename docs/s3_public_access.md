# S3 bucket: missing public access block

## What this means

The S3 bucket does not have a public access block configuration. Without it, the bucket and its objects can become publicly accessible through bucket policies, ACLs, or accidental changes. AWS recommends blocking public access by default.

## Why it matters

- Public buckets are a leading cause of data leaks and compliance violations.
- CIS and AWS best practices require blocking public access at the account or bucket level.
- A single misapplied policy or ACL can expose all objects in the bucket.

## How to fix

Add an `aws_s3_bucket_public_access_block` resource and set all four block options to `true`.

**Terraform snippet:**

```hcl
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
}

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.example.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

Apply this to every bucket; only disable specific blocks if you have a documented use case (e.g. static website with a controlled policy).

## References

- [AWS Blocking public access to your S3 storage](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
- [aws_s3_bucket_public_access_block](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block)
