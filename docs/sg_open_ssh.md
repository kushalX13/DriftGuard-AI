# Security group: open SSH (22) or RDP (3389) to 0.0.0.0/0

## What this means

An AWS security group has an ingress rule that allows traffic from the entire internet (`0.0.0.0/0`) on port 22 (SSH) or port 3389 (RDP). Anyone on the internet can attempt to connect to those ports on resources using this security group.

## Why it matters

- **SSH (22)** and **RDP (3389)** are high-value targets for brute-force and credential stuffing. Exposing them to the world greatly increases compromise risk.
- Compliance frameworks (e.g. CIS, PCI-DSS) typically require restricting administrative access to known IP ranges.
- Open 0.0.0.0/0 on these ports is a common misconfiguration that leads to real incidents.

## How to fix

Restrict ingress to a known CIDR (e.g. VPN or bastion) and avoid 0.0.0.0/0 for 22 and 3389.

**Terraform snippet:**

```hcl
resource "aws_security_group" "example" {
  name        = "restricted-ssh-rdp"
  description = "SSH and RDP from office/VPN only"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # or your VPN/bastion CIDR
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
}
```

Remove or narrow any rule that has `cidr_blocks = ["0.0.0.0/0"]` with `from_port`/`to_port` covering 22 or 3389.

## References

- [AWS Security group rules](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- [CIS AWS Foundations – restrict SSH](https://www.cisecurity.org/benchmark/amazon_web_services)
