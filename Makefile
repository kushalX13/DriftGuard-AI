.PHONY: install fmt lint test run-sample demo api

install:
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

demo:
	chmod +x demo.sh && ./demo.sh

api:
	test -d .venv || (echo "Run 'make install' first." && exit 1)
	.venv/bin/pip install -e ".[api]" && .venv/bin/python -m scripts.cli api --port 8000

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
