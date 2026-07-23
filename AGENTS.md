# Pier — Agent Workflow Rules

> For Hermes Agent, Pi, Claude Code, Codex, OpenCode, and any other agent working in this repository.

## Repository Overview

Pier connects [Hermes Agent](https://github.com/NousResearch/hermes-agent) to [Pi](https://github.com/earendil-works/pi) — a TypeScript-native coding agent with an RPC protocol and extension system. The integration follows a three-layer composable architecture (Skill → Plugin → Extension), each independently usable at increasing integration depth.

```
pier/
├── AGENTS.md                  # This file — agent workflow rules
├── README.md                  # Project overview
├── LICENSE                    # MIT
├── docs/
│   ├── architecture/          # Architecture Decision Records and diagrams
│   │   ├── overview.md        # Complete architecture overview
│   │   ├── adr-001-integration-approach.md
│   │   ├── adr-002-communication-protocol.md
│   │   ├── adr-003-dogfooding-strategy.md
│   │   └── pier-architecture.excalidraw
│   └── research/              # Research foundation documents
│       ├── pi-architecture-deep-dive.md
│       ├── hermes-coding-agent-patterns.md
│       └── competitive-integration-landscape.md
├── src/                       # Python: Hermes-side plugin and skill (future)
├── extensions/                # TypeScript: Pi extensions (future)
├── tests/                     # Test suites (future)
├── mkdocs.yml                 # Documentation site config (future)
├── pyproject.toml             # Python project config (future)
├── package.json               # TypeScript project config (future)
└── .github/
    └── workflows/             # CI/CD (future)
```

**Tech stack:**
- **Hermes-side** (Layer 1-2): Python — skill, plugin, protocol library
- **Pi-side** (Layer 3): TypeScript — ACP adapter, Hermes-specific extensions

## Development Workflow

Every change flows through five stages. Do not skip stages.

```
Spec → TDD → Implement → Review → Publish Docs
```

### 1. Spec-First

Before writing code, write a spec. Every feature, protocol change, or architectural decision starts as a document:

- **Features / design decisions** → `docs/architecture/` using the ADR template
- **Research** → `docs/research/` as reference analysis documents
- **Specs are the source of truth.** Implementation follows the spec, not the other way around.

ADR template:
```markdown
# ADR-NNN: Title

* **Status:** Proposed | Accepted | Deprecated | Superseded
* **Date:** YYYY-MM-DD
* **Author:** <name>
* **Supersedes:** ADR-NNN (if any)
* **Superseded by:** ADR-NNN (if any)

## Context
## Decision
## Rationale
## Consequences
## Alternatives Considered
## References
```

### 2. TDD (Test-Driven Development)

Tests before implementation. Period.

- **Red:** Write a failing test that defines the expected behavior.
- **Green:** Write the minimum code to make the test pass.
- **Refactor:** Clean up the code while keeping tests green.
- **Commit at green.** Every commit must pass its own tests.

Test structure mirrors source:
```
src/pier/plugin/rpc_handler.py   →   tests/plugin/test_rpc_handler.py
extensions/hermes-tools.ts       →   extensions/__tests__/hermes-tools.test.ts
```

### 3. Implement

Code to the spec. Implementation rules:

- **ADR-001 governs integration layering.** Every feature belongs to exactly one layer (Skill, Plugin, or Extension). Do not mix layer boundaries.
- **ADR-002 governs protocol.** Layer 2 uses Pi's native RPC protocol (JSONL over stdin/stdout). JSON mode is a fallback, never the primary channel.
- **ADR-003 governs rollout.** Dogfooding phases must be respected. Do not enable features in production before their phase gates pass.
- **Worktrees are mandatory.** All Pier file modifications happen in git worktrees. The main repository is never directly modified by agent operations.

### 4. Review

All code is reviewed. No exceptions.

- **Every PR requires at least one approving review.**
- **Review verdicts are posted to GitHub** via `gh pr review --comment` (or `--approve` / `--request-changes`).
- The reviewer checks: spec compliance, test coverage, layer boundaries (ADR-001), protocol correctness (ADR-002), and dogfooding phase alignment (ADR-003).
- **Self-reviews count.** If you are the only contributor, self-review with the same checklist and leave a comment explaining what you checked.

### 5. Publish Docs

Documentation is not optional. It is part of the definition of done.

- **`mkdocs build --strict` must pass.** The `--strict` flag treats warnings as errors — broken links, missing pages, and invalid markup block the build.
- **Docs live in `docs/`** and are published to GitHub Pages on merge to `main`.
- After merge, **verify GitHub Pages deployment** succeeded before closing the PR. A green CI check on the `pages-build-deployment` workflow is the verification signal.

## Coding Standards

### Python (ruff)

All Python code is formatted and linted with [ruff](https://docs.astral.sh/ruff/).

- **Formatter:** `ruff format` (replaces Black)
- **Linter:** `ruff check` (replaces Flake8, isort, pyupgrade, and dozens more)
- **Configuration:** `pyproject.toml` under `[tool.ruff]`

Required rules (enforced in CI):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM", "TCH", "RUF"]
```

Before every commit:
```bash
ruff format src/ tests/
ruff check src/ tests/
```

### TypeScript (prettier + eslint)

All TypeScript code is formatted with [Prettier](https://prettier.io) and linted with [ESLint](https://eslint.org).

- **Formatter:** `prettier --write` (single quotes, trailing commas, 100 char width)
- **Linter:** `eslint` with `@typescript-eslint` parser
- **Configuration:** `prettier.config.js`, `eslint.config.mjs`

Before every commit:
```bash
prettier --write 'extensions/**/*.ts'
eslint 'extensions/**/*.ts'
```

### Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

Body (optional).
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`
Scopes: `skill`, `plugin`, `extension`, `protocol`, `docs`, `ci`, `tests`

## PR Process

1. **Branch from `main`.** Use `feature/<name>`, `fix/<name>`, `docs/<name>`, or `ci/<name>`.
2. **Work in a git worktree** when using Pier itself to modify the repo. The main checkout is never the target of agent file operations.
3. **Create a PR** using `gh pr create`:
   ```bash
   gh pr create \
     --title "feat(plugin): add RPC event streaming" \
     --body "## Summary
   ..." \
     --base main
   ```
4. **CI gates** (when configured):
   - `ruff check && ruff format --check` (Python)
   - `prettier --check && eslint` (TypeScript)
   - `pytest` (Python tests)
   - `npm test` (TypeScript tests)
   - `mkdocs build --strict` (documentation)
5. **Request review.** Use `gh pr review` for all verdicts.
6. **Address feedback.** Push fixup commits, squash when ready.
7. **Merge.** Squash-merge (`gh pr merge --squash --delete-branch`). The merge commit message must follow Conventional Commits.
8. **Verify docs deployed** to GitHub Pages after merge.

## Review Rule

All review verdicts are posted to GitHub, never left as inline-only comments outside the PR. Use:

```bash
gh pr review <PR> --comment   # General feedback, non-blocking
gh pr review <PR> --approve   # Approve
gh pr review <PR> --request-changes  # Changes required
```

Every review comment must:
- Reference the relevant ADR or spec when applicable
- Be specific about what needs to change and why
- Distinguish blocking issues from suggestions

## Dogfooding Rule

**All changes must be tested against a local Hermes installation before merge.** This is the dogfooding rule — Pier is built to improve Hermes's coding-agent delegation, so Pier's own development uses Pier where possible.

- **Layer 1 (Skill):** Test by delegating a real task through the skill. Verify output correctness.
- **Layer 2 (Plugin):** Test with structured RPC events. Verify streaming, cancellation, and session management behave correctly.
- **Layer 3 (Extension):** Test with ACP bridge. Verify session lifecycle and cross-provider auth passthrough.

Dogfooding follows the phased rollout in [ADR-003](docs/architecture/adr-003-dogfooding-strategy.md):
- Phase 1: Side-by-side with existing coding agent skills
- Phase 2: Shadow mode (RPC logged, not acted on)
- Phase 3: Primary with terminal fallback
- Phase 4: Full switch

During development of Pier itself, dogfood at the highest layer currently available. When Layer 2 is stable, use Layer 2 to implement Layer 3. The toolchain eats its own tail.

## Architecture Decision Records

Pier's architecture is documented through ADRs in `docs/architecture/`. Every agent working here must read these before making architectural decisions:

| ADR | Title | Key Decision |
|-----|-------|-------------|
| [ADR-001](docs/architecture/adr-001-integration-approach.md) | Three-Layer Composable Integration | Skill → Plugin → Extension, each independently usable |
| [ADR-002](docs/architecture/adr-002-communication-protocol.md) | RPC as Primary Protocol | Pi's native JSONL RPC for Layer 2, with JSON mode fallback |
| [ADR-003](docs/architecture/adr-003-dogfooding-strategy.md) | Dogfooding Strategy | 4-phase rollout after Layer 2 stable, with quantitative gates |

New architectural decisions → new ADR. Existing ADRs are living documents — update their status when superseded.

**See [docs/architecture/overview.md](docs/architecture/overview.md)** for the complete architecture diagram, communication flow, and research foundation.

## Quick Reference

| Rule | Command / Check |
|------|----------------|
| Python format | `ruff format src/ tests/` |
| Python lint | `ruff check src/ tests/` |
| Python test | `pytest` |
| TS format | `prettier --write 'extensions/**/*.ts'` |
| TS lint | `eslint 'extensions/**/*.ts'` |
| TS test | `npm test` |
| Docs build | `mkdocs build --strict` |
| Create PR | `gh pr create --title "..." --body "..." --base main` |
| Review | `gh pr review <N> --comment` / `--approve` / `--request-changes` |
| Merge | `gh pr merge --squash --delete-branch` |
| Verify deploy | Check `pages-build-deployment` workflow in repo Actions |

---

*These rules apply to all agents — Hermes, Pi, Claude Code, Codex, OpenCode, and human contributors alike. When in doubt, refer to the ADRs.*
