# AGENTS.md — Pier Development Rules

Rules for AI coding agents (Hermes, Claude Code, Codex, Pi) working on this repository. Follow these or the PR gets sent back.

## 1. Documentation is the deliverable

Every feature lands with docs, not as a follow-up. A PR without updated docs is incomplete:

- ADRs in `docs/architecture/` for design decisions
- Research notes in `docs/research/` for investigation findings
- `mkdocs build --strict` must pass (no broken links, no warnings)

## 2. Review on GitHub

Code is reviewed on GitHub via pull requests. No direct pushes to `main`. Draft PRs are fine for work in progress — just make sure the CI is green before marking ready for review.

## 3. Conventional Commits

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): short description

Longer body explaining the what and why, not the how.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`

## 4. CI Gates

Every PR must pass:

| Gate | Command |
|------|---------|
| Python lint | `ruff check pier/ tests/` |
| Python format | `ruff format --check pier/ tests/` |
| Python tests | `pytest tests/ -v` |
| TypeScript lint | `npm run lint` |
| TypeScript typecheck | `npm run typecheck` |
| Docs build | `mkdocs build --strict` |

Run `make check` locally before pushing.

## 5. Testing

- Python: pytest with asyncio auto mode
- TypeScript: vitest
- Tests live under `tests/` (Python) or alongside source (TypeScript)

## 6. Python + TypeScript Parity

Pier is dual-language. When adding a feature that spans both:
- The Python plugin exposes tools/skills to the Hermes orchestrator
- The TypeScript extension provides client-side tool defs and UI
- Keep the protocol between them stable

## 7. Project Structure

```
pier/
├── pier/                   # Python plugin (Hermes side)
│   ├── __init__.py
│   └── plugin.py
├── tests/                  # Python tests
├── packages/
│   └── pier-extension/     # TypeScript extension
│       ├── src/
│       └── test/
├── docs/
│   ├── architecture/       # ADRs
│   └── research/           # background research
├── mkdocs.yml
├── pyproject.toml
├── package.json            # npm workspace root
├── Makefile
├── README.md
├── CONTRIBUTING.md
└── AGENTS.md               # ← this file
```
