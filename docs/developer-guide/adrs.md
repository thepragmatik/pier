# Architecture Decision Records (ADRs)

Pier's design is driven by Architecture Decision Records — lightweight documents that
capture important architectural decisions, the context in which they were made, and their
consequences.

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](../architecture/adr-001-integration-approach.md) | Integration Approach — Three-Layer Architecture | Accepted |
| [ADR-002](../architecture/adr-002-communication-protocol.md) | Communication Protocol — JSONL RPC over stdio | Accepted |
| [ADR-003](../architecture/adr-003-dogfooding-strategy.md) | Dogfooding Strategy — Building Pier with Pier | Accepted |

## What Is an ADR?

An ADR is a document that captures a significant architectural decision along with:

- **Context** — What is the problem we're solving?
- **Decision** — What did we choose and why?
- **Consequences** — What becomes easier? What becomes harder?
- **Alternatives Considered** — What else did we evaluate?

ADRs live alongside the code they govern. They're immutable once accepted — new decisions
get new ADRs. Superseded ADRs are marked as such but never deleted.

## Creating a New ADR

1. Copy the template: `cp docs/architecture/adr-template.md docs/architecture/adr-NNN-title.md`
2. Fill in the sections: Context, Decision, Consequences, Alternatives
3. Open a PR for review
4. Once merged, the ADR is accepted and immutable

ADRs are numbered sequentially. Check the [architecture index](../architecture/index.md) for
the latest number.

## Why ADRs?

Pier is an integration bridge — its design involves tradeoffs between simplicity, power,
and compatibility. ADRs make those tradeoffs explicit so future contributors (and our
future selves) understand _why_ the code looks the way it does, not just _how_ it works.
