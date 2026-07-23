# Blog

Iteration changelogs and development updates for Pier.

---

## Iteration 0 — Foundation

**2026-07-23**

Pier is born! This foundational iteration establishes the project structure, research
foundations, architecture, and public documentation.

### What We Shipped

- **Research (Phase R):** Three deep-dive research documents analyzing Pi's architecture,
  Hermes coding-agent patterns, and the competitive integration landscape
  ([Issue #6](https://github.com/thepragmatik/pier/issues/6))
- **Architecture (ADR):** Three Architecture Decision Records accepted:
    - ADR-001: Three-layer integration approach (Skill → Plugin → Extension)
    - ADR-002: JSONL RPC over stdio for structured communication
    - ADR-003: Dogfooding strategy — using Pier to build Pier
- **Architecture Diagram:** Interactive Excalidraw component diagram
- **Documentation Site:** MkDocs Material site with User Guide, Developer Guide,
  API Reference, Architecture, and Research sections
- **GitHub Pages:** Automated deployment workflow via GitHub Actions

### Coming in Iteration 1

- Layer 1 implementation: terminal subprocess skill wrapper
- Layer 2 scaffolding: RPC protocol bridge
- Core types and session management
- Initial test suite with Pi integration tests

---

*This blog is the canonical changelog for Pier. Each entry captures what was shipped in
an iteration, linking to relevant PRs and issues.*
