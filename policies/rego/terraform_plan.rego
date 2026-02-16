# DriftGuard OPA/Conftest policies for Terraform plan JSON (terraform show -json tfplan).
# Input: plan JSON with resource_changes[].change.after.
# Syntax: Rego v1 (OPA 2.x / Conftest with "if" and "contains").

package main

import rego.v1

# Deny: aws_security_group with ingress from 0.0.0.0/0 on port 22 (SSH) or 3389 (RDP)
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_security_group"
	after := rc.change.after
	ingress := after.ingress[_]
	"0.0.0.0/0" == ingress.cidr_blocks[_]
	port_allows_22_or_3389(ingress)
	msg := sprintf("Security group %s allows 0.0.0.0/0 on SSH (22) or RDP (3389): high risk", [rc.address])
}

port_allows_22_or_3389(ingress) if {
	from := ingress.from_port
	to := ingress.to_port
	from <= 22
	22 <= to
}

port_allows_22_or_3389(ingress) if {
	from := ingress.from_port
	to := ingress.to_port
	from <= 3389
	3389 <= to
}

# Warn: aws_s3_bucket without server-side encryption configuration
warn contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_s3_bucket"
	after := rc.change.after
	not has_server_side_encryption(after)
	msg := sprintf("S3 bucket %s has no server_side_encryption_configuration", [rc.address])
}

has_server_side_encryption(bucket) if {
	cfg := bucket.server_side_encryption_configuration
	cfg != null
	count(cfg) > 0
}

# Warn: S3 bucket without public access block (aws_s3_bucket_public_access_block)
has_public_access_block contains bucket_id if {
	block := input.resource_changes[_]
	block.type == "aws_s3_bucket_public_access_block"
	bucket_id := block.change.after.bucket
}

# All S3 bucket IDs from plan
all_s3_bucket_ids contains id if {
	rc := input.resource_changes[_]
	rc.type == "aws_s3_bucket"
	id := rc.change.after.bucket
}

# True when bucket id has no public access block (bid must be ground when called)
bucket_lacks_public_access_block(bid) if {
	bid in all_s3_bucket_ids
	not bid in has_public_access_block
}

warn contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_s3_bucket"
	bucket_lacks_public_access_block(rc.change.after.bucket)
	msg := sprintf("S3 bucket %s has no public access block (aws_s3_bucket_public_access_block)", [rc.address])
}

# Warn: aws_security_group with 0.0.0.0/0 on HTTP (80) or HTTPS (443); consider WAF
port_allows_80_or_443(ingress) if {
	from := ingress.from_port
	to := ingress.to_port
	from <= 80
	80 <= to
}

port_allows_80_or_443(ingress) if {
	from := ingress.from_port
	to := ingress.to_port
	from <= 443
	443 <= to
}

warn contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_security_group"
	after := rc.change.after
	ingress := after.ingress[_]
	"0.0.0.0/0" == ingress.cidr_blocks[_]
	port_allows_80_or_443(ingress)
	msg := sprintf("Security group %s allows 0.0.0.0/0 on HTTP (80) or HTTPS (443); consider WAF", [rc.address])
}

# Warn: RDS instance without storage encryption
warn contains msg if {
	rc := input.resource_changes[_]
	rc.type == "aws_db_instance"
	after := rc.change.after
	not after.storage_encrypted
	msg := sprintf("RDS instance %s has storage_encrypted disabled", [rc.address])
}
