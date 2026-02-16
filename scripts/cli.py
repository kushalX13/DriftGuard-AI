"""CLI entrypoint: plan, policy, report, run."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from scripts.explain import run as explain_run
from scripts.plan_runner import PlanRunnerError, run as plan_run
from scripts.policy_runner import run as policy_run
from scripts.report import run as report_run

try:
    from ml.dataset import run as dataset_run
except ImportError:
    dataset_run = None

try:
    from ml.generate_synthetic import run as synth_run
except ImportError:
    synth_run = None

try:
    from ml.train import run as train_run
except ImportError:
    train_run = None

try:
    from ml.predict import run as predict_run
except ImportError:
    predict_run = None

app = typer.Typer(
    name="driftguard",
    help="Terraform drift detection and policy enforcement.",
)

POLICY_PATH = Path(__file__).resolve().parent.parent / "policies" / "rego"
DEFAULT_PLAN_JSON = Path("infra") / "tfplan.json"
REPORTS_DIR = Path("reports")

# Severity order for --fail-on: fail if any count at this level or higher is > 0
FAIL_ON_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def _should_fail_on(findings_path: Path, fail_on: str) -> tuple[bool, str]:
    """Return (should_fail, message). fail_on is e.g. 'critical' or 'high' (case-insensitive)."""
    if not findings_path.exists():
        return False, ""
    data = json.loads(findings_path.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    level = fail_on.lower().strip()
    if level not in FAIL_ON_SEVERITY_ORDER:
        return False, ""
    idx = FAIL_ON_SEVERITY_ORDER.index(level)
    total = sum(summary.get(FAIL_ON_SEVERITY_ORDER[i], 0) for i in range(idx + 1))
    if total == 0:
        return False, ""
    return True, f"Fail-on threshold '{fail_on}' exceeded: {total} finding(s) at or above this severity (see reports/findings.json)"


@app.command()
def plan(
    tf_dir: str = typer.Option(
        "infra",
        "--tf-dir",
        "-d",
        help="Path to Terraform config directory",
    ),
    out: str = typer.Option(
        "infra/tfplan.json",
        "--out",
        "-o",
        help="Output path for plan JSON (terraform show -json tfplan)",
    ),
    fallback_sample: str | None = typer.Option(
        None,
        "--fallback-sample",
        help="If plan fails (e.g. no AWS creds), copy this file to --out and succeed (e.g. policies/examples/sample_plan.json)",
    ),
    no_fmt_check: bool = typer.Option(
        False,
        "--no-fmt-check",
        help="Skip terraform fmt -check -recursive",
    ),
    sample_only: bool = typer.Option(
        False,
        "--sample-only",
        help="Skip Terraform entirely; copy --fallback-sample to --out (demo without Terraform installed)",
    ),
) -> None:
    """Run terraform init, validate, plan, and write plan JSON. Use --fallback-sample to demo without AWS creds; use --sample-only to skip Terraform (e.g. no Terraform installed)."""
    console = Console()
    try:
        written = plan_run(
            tf_dir,
            out,
            fmt_check=not no_fmt_check,
            fallback_sample=fallback_sample,
            sample_only=sample_only,
        )
        console.print(f"Wrote [green]{written}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except PlanRunnerError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def policy(
    plan_json: str = typer.Option(
        str(DEFAULT_PLAN_JSON),
        "--plan",
        "-p",
        help="Path to plan JSON file (terraform show -json tfplan output)",
    ),
    output: str = typer.Option(
        str(REPORTS_DIR / "findings.json"),
        "--output",
        "-o",
        help="Output path for normalized findings JSON",
    ),
    policy_path: str = typer.Option(
        str(POLICY_PATH),
        "--policies",
        help="Path to Rego policies directory",
    ),
) -> None:
    """Evaluate plan with Conftest and write normalized reports/findings.json."""
    plan_path = Path(plan_json)
    out_path = Path(output)
    policies = Path(policy_path)
    try:
        report = policy_run(plan_path, policies, out_path)
        s = report.summary
        typer.echo(
            f"Wrote {out_path} — critical={s.critical} high={s.high} medium={s.medium} low={s.low} info={s.info}"
        )
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except (ValueError, OSError) as e:
        typer.echo(f"Policy run failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def explain(
    findings_json: str = typer.Option(
        str(REPORTS_DIR / "findings.json"),
        "--findings",
        "-f",
        help="Path to findings JSON from policy command",
    ),
    output: str = typer.Option(
        str(REPORTS_DIR / "explanations.json"),
        "--output",
        "-o",
        help="Output path for explanations JSON",
    ),
) -> None:
    """Attach remediation docs to findings (deterministic retrieval). Writes reports/explanations.json."""
    try:
        explain_run(findings_json, output)
        typer.echo(f"Wrote {output}")
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except (ValueError, OSError) as e:
        typer.echo(f"Explain failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def report(
    explanations: str = typer.Option(
        str(REPORTS_DIR / "explanations.json"),
        "--explanations",
        "-e",
        help="Path to explanations JSON (from explain command)",
    ),
    findings: str = typer.Option(
        str(REPORTS_DIR / "findings.json"),
        "--findings",
        "-f",
        help="Fallback: path to findings JSON if explanations missing",
    ),
    output: str = typer.Option(
        str(REPORTS_DIR / "report.md"),
        "--output",
        "-o",
        help="Output report markdown path",
    ),
) -> None:
    """Generate report.md from findings + explanations (summary table, collapsible findings)."""
    try:
        report_run(explanations, output, findings_path=findings)
        typer.echo(f"Wrote {output}")
    except FileNotFoundError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except (ValueError, OSError) as e:
        typer.echo(f"Report failed: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    plan: str = typer.Option(
        str(DEFAULT_PLAN_JSON),
        "--plan",
        "-p",
        help="Path to Terraform plan JSON (terraform show -json tfplan output)",
    ),
    fail_on: str | None = typer.Option(
        None,
        "--fail-on",
        envvar="FAIL_ON",
        help="Fail the run (exit 1) if findings at this severity or higher exist (e.g. critical, high). Use 'none' or leave unset to never fail. Env: FAIL_ON.",
    ),
    enable_ml: bool = typer.Option(
        False,
        "--enable-ml",
        help="Run ML severity/risk scoring if model exists; default is policy-only.",
    ),
) -> None:
    """Full pipeline: policy → explain → report (policy-only by default). Use --enable-ml to add ML risk scoring."""
    console = Console()
    plan_path = Path(plan)
    if not plan_path.exists():
        console.print(f"[red]Plan file not found: {plan_path}[/red]")
        raise typer.Exit(1)

    findings_path = REPORTS_DIR / "findings.json"
    explanations_path = REPORTS_DIR / "explanations.json"
    risk_scores_path = REPORTS_DIR / "risk_scores.json"
    report_path = REPORTS_DIR / "report.md"
    model_path = Path("ml/models/severity_model.pkl")

    try:
        console.print("[dim]1/3[/dim] Policy (Conftest) → findings.json")
        policy_run(plan_path, POLICY_PATH, findings_path)
        console.print("[dim]2/3[/dim] Explain (retrieval) → explanations.json")
        explain_run(findings_path, explanations_path)
        step = 3
        ml_ran = False
        if enable_ml and model_path.exists() and predict_run is not None:
            ml_ran = predict_run(findings_path, model_path, risk_scores_path)
            if ml_ran:
                console.print("[dim]3/4[/dim] Predict (ML) → risk_scores.json")
                step = 4
        if step == 3:
            console.print("[dim]3/3[/dim] Report → report.md")
        else:
            console.print("[dim]4/4[/dim] Report → report.md")
        report_run(
            explanations_path,
            report_path,
            findings_path=findings_path,
            include_risk_scores=enable_ml,
        )
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except (ValueError, OSError) as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        if "conftest" in str(e).lower():
            console.print("[dim]Install Conftest: brew install conftest[/dim]")
        raise typer.Exit(1)

    table = Table(title="Outputs", show_header=True, header_style="bold")
    table.add_column("Step", style="dim")
    table.add_column("Path")
    table.add_row("Findings", str(findings_path))
    table.add_row("Explanations", str(explanations_path))
    if enable_ml and risk_scores_path.exists():
        table.add_row("Risk scores", str(risk_scores_path))
    table.add_row("Report", str(report_path))
    console.print(table)

    if fail_on and fail_on.strip().lower() != "none":
        should_fail, msg = _should_fail_on(findings_path, fail_on)
        if should_fail:
            console.print(f"[red]{msg}[/red]")
            raise typer.Exit(1)


@app.command()
def synth(
    out: str = typer.Option(
        "ml/data/synthetic_findings.csv",
        "--out",
        "-o",
        help="Output CSV path for synthetic findings",
    ),
    n_rows: int = typer.Option(
        2500,
        "--rows",
        "-n",
        help="Number of synthetic rows to generate (2000–3000 recommended)",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        "-s",
        help="Random seed for reproducibility",
    ),
) -> None:
    """Generate synthetic findings CSV for ML (same schema as findings.csv)."""
    if synth_run is None:
        console = Console()
        console.print("[red]ml.generate_synthetic not available (install pandas).[/red]")
        raise typer.Exit(1)
    console = Console()
    try:
        df = synth_run(out, n_rows=n_rows, seed=seed)
        console.print(f"Wrote [green]{out}[/green] ({len(df)} rows)")
    except Exception as e:
        console.print(f"[red]Synth failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def train(
    csv: str = typer.Option(
        "ml/data/synthetic_findings.csv",
        "--csv",
        "-c",
        help="Path to findings CSV (synthetic or real)",
    ),
    model_out: str = typer.Option(
        "ml/models/severity_model.pkl",
        "--model-out",
        "-o",
        help="Output path for trained pipeline (joblib)",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        "-s",
        help="Random seed for train/val split",
    ),
    model_type: str = typer.Option(
        "LogisticRegression",
        "--model",
        "-m",
        help="Classifier: LogisticRegression or RandomForest",
    ),
) -> None:
    """Train baseline severity classifier; log to MLflow and save pipeline."""
    if train_run is None:
        console = Console()
        console.print("[red]ml.train not available (install pandas, scikit-learn, mlflow).[/red]")
        raise typer.Exit(1)
    console = Console()
    try:
        metrics = train_run(csv, model_out, seed=seed, model_type=model_type)
        console.print(f"Saved [green]{model_out}[/green]")
        rec3 = metrics.get("recall_class_3")
        rec3_str = f" recall_class_3={rec3:.2f}" if rec3 is not None else ""
        console.print(f"accuracy={metrics['accuracy']:.4f} macro_f1={metrics['macro_f1']:.4f}{rec3_str} (rows={metrics['rows']})")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Train failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dataset(
    findings: str = typer.Option(
        str(REPORTS_DIR / "findings.json"),
        "--findings",
        "-f",
        help="Path to findings JSON",
    ),
    out: str = typer.Option(
        "ml/data/findings.csv",
        "--out",
        "-o",
        help="Output CSV path",
    ),
) -> None:
    """Convert findings.json to a tabular dataset (CSV) for ML. Each row = one finding."""
    if dataset_run is None:
        console = Console()
        console.print("[red]ml.dataset not available (install pandas).[/red]")
        raise typer.Exit(1)
    console = Console()
    try:
        df = dataset_run(findings, out)
        console.print(f"Wrote [green]{out}[/green] ({len(df)} rows)")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        if "findings" in str(e).lower():
            console.print("[dim]Generate it first: python -m scripts.cli plan --tf-dir infra -o infra/tfplan.json --fallback-sample policies/examples/sample_plan.json --sample-only && python -m scripts.cli run --plan infra/tfplan.json[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Dataset failed: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
