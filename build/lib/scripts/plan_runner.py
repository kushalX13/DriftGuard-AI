"""Run Terraform init, validate, plan, and export plan JSON. Optional fallback to sample on plan failure."""

import subprocess
from pathlib import Path


class PlanRunnerError(Exception):
    """Raised when init or validate fails, or plan fails without fallback."""

    pass


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )


def run(
    tf_dir: str | Path,
    out_path: str | Path,
    *,
    backend: bool = False,
    fmt_check: bool = True,
    fallback_sample: str | Path | None = None,
    sample_only: bool = False,
) -> Path:
    """
    Run terraform init -backend=false, validate, plan -out=tfplan, show -json tfplan > out.
    Return path to written plan JSON. Raise PlanRunnerError on init/validate failure.
    If plan fails and fallback_sample is set, copy it to out_path and return out_path.
    If sample_only is True, copy fallback_sample to out_path and return (no Terraform required).
    """
    tf_dir = Path(tf_dir).resolve()
    out_path = Path(out_path).resolve()

    if sample_only:
        if not fallback_sample:
            raise PlanRunnerError("--sample-only requires --fallback-sample")
        sample = Path(fallback_sample)
        if not sample.exists():
            raise FileNotFoundError(f"Fallback sample not found: {sample}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(sample.read_text(), encoding="utf-8")
        return out_path

    if not tf_dir.is_dir():
        raise FileNotFoundError(f"Terraform directory not found: {tf_dir}")

    env = {"TF_INPUT": "0"}

    # 1. terraform init -backend=false
    r = _run(["terraform", "init", "-backend=false"], cwd=tf_dir, env=env)
    if r.returncode != 0:
        raise PlanRunnerError(f"terraform init failed: {r.stderr or r.stdout}")

    # 2. terraform fmt -check -recursive (optional)
    if fmt_check:
        r = _run(["terraform", "fmt", "-check", "-recursive"], cwd=tf_dir, env=env)
        if r.returncode != 0:
            raise PlanRunnerError(
                f"terraform fmt -check failed (run 'terraform fmt -recursive' in {tf_dir}): {r.stderr or r.stdout}"
            )

    # 3. terraform validate
    r = _run(["terraform", "validate"], cwd=tf_dir, env=env)
    if r.returncode != 0:
        raise PlanRunnerError(f"terraform validate failed: {r.stderr or r.stdout}")

    # 4. terraform plan -out=tfplan
    r = _run(["terraform", "plan", "-out=tfplan", "-no-color"], cwd=tf_dir, env=env)
    if r.returncode != 0:
        if fallback_sample:
            sample = Path(fallback_sample)
            if not sample.exists():
                raise FileNotFoundError(f"Fallback sample not found: {sample}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(sample.read_text(), encoding="utf-8")
            return out_path
        raise PlanRunnerError(
            f"terraform plan failed (e.g. missing AWS creds). Use --fallback-sample to use sample plan: {r.stderr or r.stdout}"
        )

    # 5. terraform show -json tfplan > out
    r = _run(["terraform", "show", "-json", "tfplan"], cwd=tf_dir, env=env)
    if r.returncode != 0:
        raise PlanRunnerError(f"terraform show -json failed: {r.stderr or r.stdout}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(r.stdout, encoding="utf-8")
    return out_path
