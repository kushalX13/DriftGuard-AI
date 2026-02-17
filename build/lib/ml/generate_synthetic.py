"""Generate synthetic findings CSV matching the schema of findings.csv for ML training.

Severity levels 0-4 match ml.dataset.SEVERITY_TO_INT: 0=CRITICAL, 1=HIGH, 2=MEDIUM, 3=LOW, 4=INFO.
"""

import random
from pathlib import Path

import pandas as pd

RANDOM_SEED = 42
CHANGE_ACTIONS = ["create", "update", "delete"]
SEVERITY_FLIP_PROB = 0.10

# Rule definitions aligned with scripts/policy_runner PATTERNS. Severity = policy authority.
# (rule_id, resource_type, service, base_severity, port_options, public_cidr_prob)
# base_severity 0-4 = CRITICAL, HIGH, MEDIUM, LOW, INFO (dataset.SEVERITY_TO_INT)
RULES = [
    ("DG-SG-OPEN-SSH", "aws_security_group", "sg", 0, [22], 0.85),           # CRITICAL
    ("DG-SG-OPEN-HTTP", "aws_security_group", "sg", 2, [80, 443], 0.6),     # MEDIUM
    ("DG-S3-NO-ENCRYPTION", "aws_s3_bucket", "s3", 1, [-1], 0.3),           # HIGH
    ("DG-S3-NO-PUBLIC-ACCESS-BLOCK", "aws_s3_bucket", "s3", 1, [-1], 0.2),  # HIGH
    ("DG-RDS-NO-ENCRYPTION", "aws_db_instance", "rds", 1, [-1], 0.2),       # HIGH
    ("DG-UNKNOWN", "unknown", "other", 2, [-1], 0.0),                      # MEDIUM fallback
]


def _flip_severity(severity: int, rng: random.Random) -> int:
    """With SEVERITY_FLIP_PROB, flip to an adjacent severity (0-4)."""
    if rng.random() >= SEVERITY_FLIP_PROB:
        return severity
    delta = rng.choice([-1, 1])
    return max(0, min(4, severity + delta))


def generate_synthetic(n_rows: int = 2500, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate n_rows synthetic findings. Reproducible if seed is fixed. label_severity in 0-4."""
    rng = random.Random(seed)
    rows = []
    # weights per rule (6 rules); matches policy rule mix
    weights = [0.22, 0.20, 0.20, 0.18, 0.15, 0.05]
    rule_indices = list(range(len(RULES)))

    for _ in range(n_rows):
        idx = rng.choices(rule_indices, weights=weights, k=1)[0]
        rule_id, resource_type, service, base_severity, port_options, public_prob = RULES[idx]
        port = rng.choice(port_options)
        has_public_cidr = rng.random() < public_prob
        change_action = rng.choice(CHANGE_ACTIONS)
        label_severity = _flip_severity(base_severity, rng)
        rows.append({
            "rule_id": rule_id,
            "resource_type": resource_type,
            "has_public_cidr": has_public_cidr,
            "port": port,
            "service": service,
            "change_action": change_action,
            "label_severity": label_severity,
        })
    return pd.DataFrame(rows)


def run(out_path: str | Path, n_rows: int = 2500, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate synthetic CSV and write to out_path. Returns DataFrame."""
    df = generate_synthetic(n_rows=n_rows, seed=seed)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df
