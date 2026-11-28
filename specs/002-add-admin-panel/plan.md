# Implementation Plan — Football Admin Panel

**Branch** — `add-admin-panel`

**Date** — 2026-11-28

**Spec** — [Football Admin Panel](spec.md)

## Summary

Add a browser panel for Players, Fixtures, and Availability. Run a separate loopback-only
FastAPI app with plain HTML, CSS, and JavaScript. Admin routes delegate to a service and
PostgreSQL repositories. One transaction saves all pending availability changes for the
selected fixture. Confirmed deletes remove linked availability while protecting goalkeeper
history. The existing football HTTP API, MCP tools, and chat retain their contracts.

## Technical Context

| Area | Decision |
| --- | --- |
| Language | Python 3.12+ and native browser HTML, CSS, and JavaScript |
| Dependencies | Existing FastAPI, Uvicorn, and Psycopg. Reuse the project's packaging and pytest setup. |
| Storage | Existing PostgreSQL tables and constraints on the project's Compose and CI PostgreSQL 18 baseline. Reuse the connection configuration with admin-specific connection and transaction deadlines. |
| Testing | Pytest for service and HTTP behavior, isolated PostgreSQL integration tests, and browser acceptance checks from the quickstart |
| Target | Local workstation at `http://127.0.0.1:8002/admin` via `make admin` |
| Project type | A browser and local HTTP entry point in the existing Python package |
| Performance | Update and verify three statuses with one save within 60 seconds with 25 players and two fixtures. Measure on a local workstation with an unthrottled browser and local PostgreSQL. |
| Constraints | No new framework, build step, schema migration, or changes to existing API contracts. Ask the maintainer first if an existing API change becomes necessary. |
| Scope | One coach, one team's data, three pages, and one fixture per availability save |

## Constitution Check

| Principle | Before research | After design |
| --- | --- | --- |
| I. Code quality and boundaries | Use existing web and storage dependencies. Keep database work in repositories. | Pass. The admin app owns browser and HTTP details, a service owns validation and domain results, and repositories own parameterized SQL and transactions. The agent and optimizer remain outside the admin path. |
| II. Deterministic testing | Verify the admin HTTP and real PostgreSQL boundaries separately. | Pass. Stub the service for HTTP tests. Use an isolated test database for rollback, row isolation, repeat saves, guarded deletion, and compatibility queries. Existing agent and chat tests can run with their existing stubs. |
| III. Consistent coach experience | Use the same player, fixture, rating, and availability rules as the agent. | Pass. Only explicit Available statuses are returned by the existing lookup. Use the shared project data and existing read queries where they fit. The admin contract specifies errors and preserves inputs for recovery. |
| IV. Measurable and bounded execution | Use the spec's workload and timing target. Bound I/O through the new admin path. | Pass. The quickstart defines the measurement. Use a 3-second admin database connect timeout, a 5-second statement timeout within a 10-second batch transaction timeout, and a 15-second browser request deadline. Send no automatic mutation retries. Existing request paths use their current limits. |
| Technical constraints | Keep Ollama local, guard deletion, and avoid sensitive logging. | Pass. The admin app can run without the agent runtime. Parameterized SQL, explicit record confirmation, guarded transactions, and access checks are part of the design. Log operation and failure category without record payloads or credentials. |

No constitution exceptions identified.

## Project Structure

### Documentation

```text
specs/002-add-admin-panel/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── browser-admin.md
└── quickstart.md
```

### Proposed source changes

```text
Makefile
README.md
pyproject.toml
src/football_team_assistant/
├── db/database.py
├── services/admin_service.py
├── repositories/
│   ├── fixture_repository.py
│   ├── player_repository.py
│   └── availability_repository.py
└── web_admin/
    ├── __init__.py
    ├── app.py
    └── static/
        ├── index.html
        ├── admin.css
        └── admin.js
tests/
├── test_admin_service.py
├── api/test_web_admin.py
└── integration/test_admin_operations.py
```

Use three browser URLs with a shared static shell, packaged like the chat assets. Add
`make admin` as an independent entry point. Keep route contracts in the admin module.
Add repository methods where the existing reads lack equivalent behavior. Reuse the
existing database configuration and apply new limits only to admin operations.

## Design Phases

- Phase 0 records the web boundary, storage design, deletion guard, and verification
  decisions in [research.md](research.md).
- Phase 1 defines the [data model](data-model.md), [browser and HTTP contract](contracts/browser-admin.md),
  and [validation guide](quickstart.md). The next command, `$speckit-tasks`, decomposes the
  implementation.
