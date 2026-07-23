# Contributing

Thank you for your interest in contributing to Pier! This guide covers the development
workflow, testing, and submission process.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/thepragmatik/pier.git
cd pier

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Prerequisites for Development

- **Python 3.10+** — the core runtime
- **Node.js 18+** — for Pi (the TypeScript coding agent)
- **Pi CLI** — `npm install -g @earendil-works/pi`
- **Hermes Agent** — optional, for integration testing

## Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=pier --cov-report=term-missing

# Run a specific test file
pytest tests/test_plugin.py

# Run integration tests (requires Pi installed)
pytest tests/integration/ -m integration
```

## Project Structure

```
pier/
├── pier/                   # Main package
│   ├── __init__.py
│   ├── skill.py            # Layer 1: terminal subprocess wrapper
│   ├── plugin.py           # Layer 2: RPC protocol bridge
│   ├── extension.py        # Layer 3: ACP bridge + TypeScript extensions
│   ├── session.py          # Session management (async context managers)
│   └── types.py            # Shared types and data classes
├── skills/
│   └── pier-skill/
│       └── SKILL.md        # Hermes skill definition
├── docs/                   # This documentation site
├── tests/
│   ├── test_skill.py
│   ├── test_plugin.py
│   ├── test_extension.py
│   └── integration/
└── .github/
    └── workflows/
        ├── ci.yml
        └── docs.yml        # GitHub Pages deployment
```

## Coding Conventions

- **Python:** Black formatting, isort imports, mypy type checking
- **Docstrings:** Google style
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) format
- **PRs:** One feature or fix per PR, link to an issue

## Pre-Commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Submitting Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes with tests
3. Run the full test suite: `pytest`
4. Open a pull request against `main`
5. Ensure CI passes (lint, type check, tests)

## Documentation

This documentation site is built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).
To preview locally:

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

Open http://localhost:8000 to see the live preview.

## Questions?

Open a [GitHub Discussion](https://github.com/thepragmatik/pier/discussions) or
join the development channel on [Discord](https://discord.gg/nousresearch).
