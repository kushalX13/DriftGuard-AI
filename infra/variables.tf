# Defaults for all variables so terraform validate and plan work in CI without -var.
# Do not add required variables without defaults; CI has no -var file.

variable "aws_region" {
  description = "AWS region for provider and resources"
  type        = string
  default     = "us-east-1"
}
