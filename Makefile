.PHONY: install fmt lint test run-sample

install:
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

fmt:
	ruff format scripts/
	ruff check scripts/ --fix

lint:
	ruff check scripts/
	ruff format --check scripts/

test:
	pytest -v

run-sample:
	.venv/bin/python -m scripts.cli --help
