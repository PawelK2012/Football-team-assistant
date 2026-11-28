---
description: "Implementation tasks for the Football Admin Panel"
---

# Tasks — Football Admin Panel

**Input** — Design documents in `specs/002-add-admin-panel/`

**Prerequisites** — [Specification](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [browser contract](contracts/browser-admin.md), and
[quickstart](quickstart.md).

**Tests** — The plan and constitution require deterministic service, HTTP, and
PostgreSQL coverage. Write each story's tests before implementing its behavior and
confirm a failure for the expected reason. Use the isolated test database for writes.

**Organization** — Each P1 story has its own phase and can be verified after the
shared foundation, with seeded records where needed.

## Format

`- [ ] TNNN [P?] [USn?] Description with repository-relative file path`

`[P]` identifies tasks that can overlap within their dependency group because
they edit different files. Story labels apply to story phases only.

## Phase 1 — Setup

- [x] T001 Create the importable admin package in `src/football_team_assistant/web_admin/__init__.py`.
- [x] T002 [P] Register `index.html`, `admin.css`, and `admin.js` as admin package data in `pyproject.toml`.
- [x] T003 [P] Add `make admin` to `Makefile` using the existing locked environment and Uvicorn. Run `football_team_assistant.web_admin.app:app` on IPv4 loopback port 8002 with proxy headers and access logging disabled.

## Phase 2 — Foundational work

- [x] T004 [P] Specify admin boundary tests in `tests/api/test_web_admin.py` for loopback peer, exact Host, exact same Origin and JSON on writes, rejected duplicate headers, no-store responses, shell routes, and static asset responses.
- [x] T005 [P] Add admin database connection support in `src/football_team_assistant/db/database.py` using the existing database configuration. Apply the 3-second connection, 5-second statement, and 10-second batch transaction limits to admin connections only.
- [x] T006 [P] Create the shared shell in `src/football_team_assistant/web_admin/static/index.html`, visual styling in `src/football_team_assistant/web_admin/static/admin.css`, and page routing and request handling in `src/football_team_assistant/web_admin/static/admin.js`. Provide direct links, labeled controls, visible focus, live status feedback, and responsive charcoal panels with light primary buttons. Apply the 15-second browser deadline, prevent repeat writes while pending, and reload saved data before offering manual retry of an unknown outcome.
- [x] T007 Implement the standalone app and boundary from `specs/002-add-admin-panel/contracts/browser-admin.md` in `src/football_team_assistant/web_admin/app.py`. Serve the three page URLs and packaged assets, redirect `/admin` to Players, enforce request checks and no-store, and map validation and domain errors to the documented envelope. Use synchronous handlers for blocking database operations and log only operation and failure category.
- [x] T008 [P] Add the shared admin roster read in `src/football_team_assistant/repositories/player_repository.py`. Use admin database limits and return all player fields in name and ID order. Preserve the existing available-player lookup.
- [x] T009 [P] Add the shared admin fixture read in `src/football_team_assistant/repositories/fixture_repository.py`. Use admin database limits and return all past and upcoming fixtures in date and ID order. Preserve the existing fixture reads.
- [x] T010 Expose the two shared list reads through `src/football_team_assistant/services/admin_service.py` and the admin GET routes in `src/football_team_assistant/web_admin/app.py`. Return empty arrays for empty lists and use the shared storage-error mapping.

**Checkpoint** — The loopback app serves the shared shell and both lists with
the existing database schema. Every story can use these reads.

## Phase 3 — User Story 1 · Record availability for a fixture (P1)

**Goal** — View the full roster for one fixture and save all pending status changes together.

**Independent test** — Use two seeded fixtures and a seeded roster. Change two
statuses for the first fixture, save once, reload, and verify the changes and the
existing agent lookup. Switch fixtures to verify the second fixture stayed intact,
and exercise both outcomes of discarding pending changes.

### Tests

- [x] T011 [P] [US1] Add GET and PUT availability contract tests in `tests/api/test_web_admin.py`. Cover the full roster, all three read states, committed batch shape, missing fixture and player, malformed values, duplicate IDs, and storage error mappings.
- [x] T012 [P] [US1] Add batch validation tests in `tests/test_admin_service.py` for a nonempty batch, unique player IDs, strict booleans, and invalid values rejected before the repository call.
- [x] T013 [P] [US1] Add availability integration tests in `tests/integration/test_admin_operations.py` using the isolated database. Cover mixed inserts and updates, forced mid-batch rollback, unchanged players and fixtures, repeated saves, last-commit precedence, persistence on reread, and the existing available-player lookup.

### Implementation

- [x] T014 [US1] Implement the fixture-scoped roster read and transactional save in `src/football_team_assistant/repositories/availability_repository.py`. Enforce the model rules “References a fixture.”, “References a player.”, and “Required boolean for an existing record. The pair of IDs forms its unique key.” Use a left join for the “No database row. Admin read returns `null`.” state and preserve explicit `true` and `false`. Lock the fixture and referenced players with key-share locks, order player locks and upserts by ID, reject missing records before writing, and return only rows committed by the batch. Preserve untouched rows and resolve overlapping changes by commit order.
- [x] T015 [US1] Wire the availability rules and domain outcomes in `src/football_team_assistant/services/admin_service.py` and GET and PUT `/admin/api/fixtures/{fixture_id}/availability` in `src/football_team_assistant/web_admin/app.py`. Enforce “a nonempty set of unique player IDs and desired booleans for one fixture” and the response and error shapes in `specs/002-add-admin-panel/contracts/browser-admin.md`.
- [x] T016 [US1] Implement the Availability page in `src/football_team_assistant/web_admin/static/admin.js`. Show all players and the three saved statuses, distinguish duplicate labels and pending edits, support undo before Save, and disable editing until a fixture is selected. Confirm before switching fixtures or opening Players or Fixtures with pending changes. Handle empty data, stale responses, missing records, and failed or unknown save outcomes with the shared request and recovery behavior.
- [x] T017 [US1] Run the availability tests in `tests/test_admin_service.py`, `tests/api/test_web_admin.py`, and `tests/integration/test_admin_operations.py`. Exercise the availability and discard scenarios in `specs/002-add-admin-panel/quickstart.md` with seeded data.

## Phase 4 — User Story 2 · Manage players (P1)

**Goal** — Create, view, edit, and delete players, with protection for goalkeeper history.

**Independent test** — From Players, create and view a player with a 3.5 rating,
edit the record, reload to confirm persistence, then cancel and confirm deletion.
Use an independently seeded player with goalkeeper history to verify the block.

### Tests

- [x] T018 [P] [US2] Add Players contract tests in `tests/api/test_web_admin.py` for list, create, edit, confirmed delete, invalid fields, missing record, and goalkeeper-history conflict.
- [x] T019 [P] [US2] Add player validation tests in `tests/test_admin_service.py` for blank and overlong names, half-point ratings and boundary values, boolean eligibility and its creation default, and required delete confirmation.
- [x] T020 [P] [US2] Add player persistence and deletion scenarios in `tests/integration/test_admin_operations.py`. Verify stable identity, availability and history preservation on edit, permitted deletion with availability cleanup, goalkeeper-history protection during concurrent insertion, and both orderings of player deletion racing a batch save. Seed availability directly for independent execution.

### Implementation

- [x] T021 [US2] Implement admin player create, edit, and guarded delete in `src/football_team_assistant/repositories/player_repository.py`. Keep IDs “Database-generated positive integer. Stable across edits.” For deletes, lock the parent, check goalkeeper history in a separate read-committed statement, and allow the existing availability cascade only when deletion is permitted.
- [x] T022 [US2] Implement player validation and mutation routes in `src/football_team_assistant/services/admin_service.py` and `src/football_team_assistant/web_admin/app.py`. Apply the model constraints “Trim surrounding whitespace. Require 1–100 characters after trimming. Names may repeat.”, “Numeric value from 1.0 through 6.0 in increments of 0.5. Validate before writing so the database cannot round an invalid input to a valid value.”, and “Boolean. Defaults to false on creation.” Require explicit confirmation and map missing records and protected history to the contract errors.
- [x] T023 [US2] Implement the Players list and forms in `src/football_team_assistant/web_admin/static/admin.js`. Distinguish duplicate names by stable ID. Retain entered values and field feedback on rejection, identify the selected player and linked availability in delete confirmation, and show successful changes in the list.
- [x] T024 [US2] Run the player scenarios in `tests/test_admin_service.py`, `tests/api/test_web_admin.py`, and `tests/integration/test_admin_operations.py`. Exercise Players creation, editing, cancel, permitted deletion, and blocked deletion from `specs/002-add-admin-panel/quickstart.md`.

## Phase 5 — User Story 3 · Manage fixtures (P1)

**Goal** — Create, view, edit, and delete past and upcoming fixtures while preserving history.

**Independent test** — From Fixtures, create and view a match, edit its date,
opponent, and designation, reload, and verify the same record. Cancel and then
confirm an eligible deletion. Use a seeded fixture with history to verify the block.
When US1 is present, also verify the saved fixture appears in its selector.

### Tests

- [x] T025 [P] [US3] Add Fixtures contract tests in `tests/api/test_web_admin.py` for listing past and upcoming records, create, edit, confirmed delete, invalid fields, stale IDs, and history conflicts.
- [x] T026 [P] [US3] Add fixture validation tests in `tests/test_admin_service.py` for calendar dates, opponent length and whitespace, both boolean designations, and required delete confirmation.
- [x] T027 [P] [US3] Add fixture integration scenarios in `tests/integration/test_admin_operations.py`. Verify stable identity, linked record preservation on edit, availability cleanup on deletion, goalkeeper-history protection during concurrent insertion, and both orderings of fixture deletion racing a batch save. Seed linked records directly for independent execution.

### Implementation

- [x] T028 [US3] Implement admin fixture create, edit, and guarded delete in `src/football_team_assistant/repositories/fixture_repository.py`. Keep IDs “Database-generated positive integer. Stable across edits.” Apply the read-committed parent lock and subsequent history check, then use the existing availability cascade when deletion is permitted.
- [x] T029 [US3] Implement fixture validation and mutation routes in `src/football_team_assistant/services/admin_service.py` and `src/football_team_assistant/web_admin/app.py`. Apply “Calendar date in ISO `YYYY-MM-DD` form, stored as `fixture_date`.”, “Trim surrounding whitespace. Require 1–150 characters after trimming.”, and “Required boolean. True means Home and false means Away.” Require explicit confirmation and return documented errors for missing records and protected history.
- [x] T030 [US3] Implement the Fixtures list and forms in `src/football_team_assistant/web_admin/static/admin.js`. Show past and upcoming fixtures, retain inputs and field feedback on rejection, and name the fixture and linked availability in delete confirmation.
- [x] T031 [US3] Run the fixture scenarios in `tests/test_admin_service.py`, `tests/api/test_web_admin.py`, and `tests/integration/test_admin_operations.py`. Exercise Fixtures creation, editing, cancel, permitted deletion, and blocked deletion from `specs/002-add-admin-panel/quickstart.md`.

## Phase 6 — Polish and cross-cutting verification

- [x] T032 [P] Document launch, host-only use, and PostgreSQL setup for the admin panel in `README.md`.
- [x] T033 [P] Build and inspect the wheel configured by `pyproject.toml`. From outside the checkout, verify that the installed app serves the packaged shell, CSS, and JavaScript described in `specs/002-add-admin-panel/contracts/browser-admin.md`.
- [ ] T034 Run the integrated browser workflow from `specs/002-add-admin-panel/quickstart.md`. Script all eight management actions and cover fixture selector updates, recovery, access from the host and attempted access from another device, keyboard use at 360 and 1280 pixels, the first-use walkthrough, and the 25-player, two-fixture, 60-second timing check. Record results and any unverified checks in the quickstart.
- [x] T035 Run the full pytest suite with the isolated database configured in `tests/conftest.py` and run Ruff lint and format checks from `pyproject.toml`. Review the implementation diff against the compatibility boundary in `specs/002-add-admin-panel/contracts/browser-admin.md` and record verification results in `specs/002-add-admin-panel/quickstart.md`.

## Dependencies and execution order

```text
Setup → Foundation → US1 ─┐
                   ├→ US2 ├→ Polish and verification
                   └→ US3 ┘
```

The graph shows feature dependencies. US1 needs only the shared lists and seeded
records. US2 and US3 can use seeded availability and history for independent
verification. Their race tests can seed or write availability directly until the
US1 repository is present, then exercise the full admin save path in final verification.
Sequence edits to shared app, service, browser, and test files to avoid conflicts.

- In setup, T002 and T003 can run together after T001.
- In the foundation, T004–T006 can run together. Finish T004–T006 before T007.
  T008 and T009 can run together after T005, then T010 joins their reads with T007.
- In US1, T011–T013 can run together after T010, before implementing T014–T016.
- In US2, T018–T020 can run together after T010 and before implementing T021–T023.
- In US3, T025–T027 can run together after T010 and before implementing T028–T030.
- Start a later story's test group after the previous story releases the shared test
  files. Finish each story with its own verification task.
- In the final phase, T032 and T033 can run together after the stories. Run T034
  before T035 so the quickstart results can be updated in order.

## Implementation strategy

Start with Availability as the MVP. Use `/admin/availability` directly with seeded
players and fixtures, then verify a batch save and fixture isolation independently.
Add Players and Fixtures to deliver the complete requested panel. Finish with the
cross-story acceptance and compatibility checks.

Preserve existing HTTP, MCP, and chat contracts throughout. If a necessary change to
an existing API is identified, ask the maintainer before making it.
