# Security group: open HTTP (80) or HTTPS (443) to 0.0.0.0/0

## What this means

An AWS security group has an ingress rule that allows traffic from the entire internet (`0.0.0.0/0`) on port 80 (HTTP) or 443 (HTTPS). The service is reachable by anyone on the internet.

## Why it matters

- Public web traffic is expected for many apps, but exposing 80/443 to 0.0.0.0/0 without WAF or rate limiting increases abuse and attack surface.
- Compliance (e.g. PCI-DSS) often requires WAF or additional controls when accepting public web traffic.
- Use a WAF (e.g. AWS WAF, CloudFront with WAF) to add rate limiting, bot protection, and rule sets.

## How to fix

Keep 80/443 open only if intentional; add AWS WAF in front (e.g. CloudFront or ALB with WAF) and restrict by geography or rate if needed.

**Terraform snippet (WAF in front of ALB):**

```hcl
resource "aws_security_group" "web" {
  name        = "allow-http-https"
  description = "HTTP/HTTPS from internet; put WAF in front"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Add aws_wafv2_web_acl and associate with ALB/CloudFront.
```

If the service is internal only, restrict `cidr_blocks` to your VPN or VPC CIDRs instead of `0.0.0.0/0`.

## References

- [AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/)
- [CIS AWS Foundations – restrict public access](https://www.cisecurity.org/benchmark/amazon_web_services)
