<!--
Sync Impact Report
Version change: unversioned scaffold → 1.0.0 (initial adoption)
Principles added:
- I. Code Quality and Clear Boundaries
- II. Deterministic Testing and Integration Coverage
- III. Consistent Coach Experience
- IV. Measurable Performance and Bounded Execution
Sections added: Technical Constraints, Development Workflow, Governance
Sections removed: none
Template changes: none required. Feature plans consume these rules through the Constitution Check.
Follow-up TODOs: none
-->

# Football Team Assistant Constitution

## Core Principles

### I. Code Quality and Clear Boundaries

The agent MUST own model interaction and tool orchestration. MCP tools and HTTP routes MUST
delegate shared football operations to application services. Repositories MUST own database
access, and the optimizer MUST own squad selection. Changes MUST follow the repository's Ruff
configuration, add type hints to new or modified functions, and reuse existing logic where it
fits. New dependencies or abstractions MUST have a concrete justification in the feature plan.

### II. Deterministic Testing and Integration Coverage

New or changed behavior MUST have focused pytest coverage for expected outcomes and relevant
failure cases. Agent tests MUST stub Ollama responses and verify tool names and arguments when
tool use is part of the behavior. Changes to MCP or HTTP contracts or PostgreSQL behavior MUST
have integration coverage at the affected boundary. Database integration tests MUST use an
isolated test database.

### III. Consistent Coach Experience

The CLI agent, MCP tools, and HTTP API MUST use the same football terminology and apply the
same domain rules to equivalent requests. The agent MUST ground claims about fixtures, player
availability, ratings, and goalkeeper history in verified data. It MUST ask for clarification
when the intended fixture is ambiguous. Each interface MUST surface actionable failures in its
established format. Changes to public inputs, outputs, or error behavior MUST be specified
explicitly and tested.

### IV. Measurable Performance and Bounded Execution

Features that affect response latency or expand the supported workload MUST define a measurable
target, a representative workload, and a test environment. Changes to an existing path MUST
compare before-and-after measurements under equivalent conditions. For squad generation, the
workload MUST include the upper supported roster size. New or changed external calls MUST have
defined timeouts, and retrying workflows MUST bound their attempts. Performance changes MUST
preserve the specified squad balance and goalkeeper rotation rules.

## Technical Constraints

Local Ollama MUST remain supported. Introducing a paid model API requires maintainer approval.
Model output and MCP responses MUST be treated as untrusted data, and model-generated tool
arguments MUST be validated before dispatch. PostgreSQL queries MUST be parameterized.
Credentials and unnecessary player data MUST be kept out of logs and committed artifacts.
Destructive database operations require explicit approval.

## Development Workflow

- Feature specs MUST define observable acceptance criteria and identify any affected public
  behavior or performance targets.
- The plan's Constitution Check MUST record the relevant layer boundaries, test coverage,
  user-facing behavior, and performance verification. Any proposed exception MUST include
  its scope and rationale.
- Before completion, run relevant tests and Ruff checks. Run the full test suite when practical
  and report any verification that could not run.

## Governance

Feature plans and implementation reviews MUST check compliance with this constitution.
Maintainer approval is required for amendments and feature-specific exceptions. Record approved
exceptions in the feature plan. Each amendment MUST record its rationale, date, and any
required updates to dependent artifacts.

Use semantic versioning for amendments. Increment MAJOR for incompatible changes or removed
principles, MINOR for new or materially expanded principles, and PATCH for clarifications.

**Version**: 1.0.0 | **Ratified**: 2026-11-28 | **Last Amended**: 2026-11-28
