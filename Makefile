# Developer convenience targets for the `oshell` package.

.PHONY: install lint fmt test cov run tui clean

install:        ## Create .venv and install core + dev + tui
	uv venv .venv
	uv pip install --python .venv -e ".[dev,tui]"

lint:           ## Lint the new core
	.venv/bin/ruff check oshell tests

fmt:            ## Auto-format / fix lint
	.venv/bin/ruff check --fix oshell tests
	.venv/bin/ruff format oshell tests

test:           ## Run the test suite
	.venv/bin/python -m pytest -q

cov:            ## Tests with coverage
	.venv/bin/python -m pytest -q --cov=oshell --cov-report=term-missing

run:            ## Launch the interactive CLI
	.venv/bin/oshell chat

tui:            ## Launch the Textual workspace
	.venv/bin/oshell tui

clean:          ## Remove caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage **/__pycache__
