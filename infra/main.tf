# Deliberately insecure examples for DriftGuard policy scanning.
# Do not apply. Use only: init, plan, and export plan JSON.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  # No credentials in repo. Use env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # or default profile if you need to run plan; otherwise use a saved tfplan.json.
}

# Insecure: S3 bucket without encryption
resource "aws_s3_bucket" "bad_bucket" {
  bucket = "my-open-bucket"
}

# Insecure: security group allowing 0.0.0.0/0 ingress
resource "aws_security_group" "open_ingress" {
  name        = "allow-all-in"
  description = "Allow all inbound (deliberately insecure)"

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
