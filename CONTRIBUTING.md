# Contributing to Pier

Thank you for your interest in contributing! Pier is an open-source integration between the [Pi coding agent](https://github.com/earendil-works/pi) and [Hermes Agent](https://github.com/nousresearch/hermes-agent).

## Getting Started

1. Fork the repository and clone it locally.
2. Install dependencies:
   ```bash
   make install       # Python (pip editable install)
   make install-js    # TypeScript (npm install)
   ```
3. Run the full check to confirm everything works:
   ```bash
   make check
   ```

## Development Workflow

- **Branch from `main`** — use a descriptive branch name: `feat/`, `fix/`, `docs/`, `ci/`
- **Lint before committing** — `make lint` covers both Python (ruff) and TypeScript (biome)
- **Write tests** — Python tests go in `tests/`, TypeScript tests live alongside source or in `packages/pier-extension/test/`
- **Keep the docs building** — `make docs` runs `mkdocs build --strict`

## Pull Requests

1. Push your branch and open a PR against `main`.
2. All CI checks must pass: ruff, pytest, npm lint + typecheck, and mkdocs.
3. Request review from a maintainer.
4. PRs are squash-merged once approved and green.

## Code Style

- **Python**: ruff with line length 120. `make fmt` to auto-format.
- **TypeScript**: biome, strict TypeScript. `npm run lint` in the workspace root.

## Architecture Decisions

Design decisions are documented as Architecture Decision Records in `docs/architecture/`. Before proposing a significant change, check whether an existing ADR covers the topic.

## Questions?

Open a [GitHub Issue](https://github.com/thepragmatik/pier/issues) or start a discussion.
