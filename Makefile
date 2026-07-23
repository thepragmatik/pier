.PHONY: lint test build check install typecheck clean fmt

# ── Python ──────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

lint: lint-py lint-js

fmt:
	ruff format plugins/ tests/
	ruff check --fix plugins/ tests/

lint-py:
	ruff check plugins/ tests/
	ruff format --check plugins/ tests/

test-py:
	python -m pytest tests/ -v

# ── TypeScript ──────────────────────────────────────────────────────

install-js:
	npm install

lint-js:
	npm run lint

typecheck:
	npm run typecheck

test-js:
	npm test

# ── Combined ────────────────────────────────────────────────────────

check: lint test

test: test-py test-js

# ── Docs ────────────────────────────────────────────────────────────

docs:
	mkdocs build --strict

docs-serve:
	mkdocs serve

# ── Clean ───────────────────────────────────────────────────────────

clean:
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -rf site/
