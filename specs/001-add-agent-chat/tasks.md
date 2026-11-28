---
description: "Implementation tasks for Football Agent Web Chat"
---

# Tasks for Football Agent Web Chat

**Design inputs** — [Specification](spec.md), [plan](plan.md), [research](research.md),
[data model](data-model.md), [browser contract](contracts/browser-chat.md), and
[validation quickstart](quickstart.md).

**Format** — `[ID] [P?] [Story?] Description`. Paths are relative to the repository root.
`[P]` marks tasks that can run in parallel with the companions listed below after their
shared prerequisites are complete.

**Tests** — Add deterministic HTTP coverage at the new browser boundary and stub Ollama and MCP
where appropriate. Use the quickstart for browser and live acceptance checks. Keep all application
changes within the new chat surface and preserve existing CLI, HTTP, MCP, and database behavior.

## Phase 1 — Setup

- [X] T001 Add the chat package at `src/football_team_assistant/web_chat/__init__.py` under the existing Python project.
- [X] T002 Configure `pyproject.toml` to include the chat HTML, CSS, and JavaScript in the Python distribution using the existing build tooling.

## Phase 2 — Foundation

- [X] T003 Create the standalone FastAPI app and route-scoped error handling in `src/football_team_assistant/web_chat/app.py`. Validate the actual loopback peer and canonical Host for pages, assets, and requests. Require canonical Origin on writes and apply the contract's no-store policy and structured errors without logging conversation IDs, prompts, replies, or player data.
- [X] T004 Set up the app lifespan in `src/football_team_assistant/web_chat/app.py`. Open and close the local Ollama client and stdio MCP session, use the active interpreter for the existing MCP module, forward configured `DATABASE_URL`, and reuse `to_ollama_tool`. Bound initialization and discovery together to 10 seconds. Keep the page available on startup failure and expose an actionable unavailable response.
- [X] T005 Implement the in-memory registry in `src/football_team_assistant/web_chat/conversations.py`. Use an “unpredictable, opaque server-issued ID”, one `FootballAgent` per conversation, and exclusive admission and completion so “Only one turn can enter pending.” Enforce a 90-second deadline around the entire agent turn, including Ollama calls, and keep the existing 10-second MCP per-call timeout. On timeout, error, empty reply, or cancellation, “truncate the agent history to its previous length and restore the selected fixture before releasing the pending turn.” Ensure the lifespan clears the registry and cancels pending work before closing upstream resources in `src/football_team_assistant/web_chat/app.py`.

## Phase 3 — User Story 1 · Ask the football agent in a browser (P1, MVP)

**Goal** — Send a football question and read the reply on the host computer. Covers FR-001,
FR-002, FR-005, the host-only constraint, and the pending state and bounded waits in FR-004.

**Independent test** — Ask which fixtures are upcoming and see an ordered question and reply
with pending feedback between them. At 360 and 1280 pixels the keyboard-only flow works without
horizontal scrolling. A stalled agent turn returns a timeout, and the browser clears pending
feedback even if the server response never arrives. A different device on the private network
cannot access the page or submit a turn.

- [X] T006 [P] [US1] Write HTTP boundary tests in `tests/api/test_web_chat.py` for page and assets, conversation creation, successful turn forwarding, blank or malformed input, unsupported content type, `409 turn_pending` on overlapping turns without a second dispatch, access rejection for non-loopback peer or incorrect Host or Origin, and safe error payloads. Stub a stalled agent turn with a short test deadline and assert cancellation and `504 turn_timeout`. Separately stub MCP initialization failure and tool discovery timeout through the app lifespan. In each startup failure case assert that the page still serves, valid chat requests receive `503 agent_unavailable` without dispatching a turn, and partially opened resources close.
- [X] T007 [P] [US1] Add host-only launch and acceptance details in `specs/001-add-agent-chat/quickstart.md` for the page and turn route, the separate existing HTTP app, and keyboard focus and long-message checks. Document how to verify that pending feedback clears after a server timeout or when no response arrives by the browser deadline.
- [X] T008 [P] [US1] Create the transcript, labeled composer, send control, and accessible status regions in `src/football_team_assistant/web_chat/static/index.html`.
- [X] T009 [P] [US1] Implement responsive layout, message wrapping, distinct coach and assistant roles, and visible focus and status styles in `src/football_team_assistant/web_chat/static/chat.css` using the selectors agreed for T008.
- [X] T010 [P] [US1] Serve `GET /chat` and its same-origin assets from module-relative packaged paths. Add the conversation creation and turn routes in `src/football_team_assistant/web_chat/app.py` with the contract envelopes. Validate “a browser-generated UUID” and “the coach's trimmed nonblank text”, delegate accepted turns, and require “a nonblank assistant reply or a failure”. Return `409 turn_pending` for overlap, `503 agent_unavailable` for unavailable infrastructure, and `504 turn_timeout` when the turn deadline expires.
- [X] T011 [US1] Connect the composer in `src/football_team_assistant/web_chat/static/chat.js`. Create the conversation at page startup with a 10-second browser deadline and keep its ID in page memory. Assign a fresh UUID per new turn, show pending before the turn request, and prevent blank or repeated submissions. Clear pending and show a plain-language error on a timeout response or after 95 seconds without a turn response. Render ordered messages as “plain text, with line breaks and distinct coach and assistant labels” and keep markup-like output inert.

**Checkpoint** — Complete the browser ask-and-reply flow with the packaged chat app. Verify
the server and browser deadlines and the degraded startup behavior before the MVP is ready.

## Phase 4 — User Story 2 · Ask a follow-up in the same conversation (P2)

**Goal** — Preserve context in an open page and isolate independent pages. Covers FR-002,
FR-003, and SC-001.

**Independent test** — Ask about North Test FC in one tab and South Test FC in another. Ask
each tab to create squads “for that game” and verify that each uses its own fixture. Reload one
tab during a delayed turn and verify that it starts empty and ignores the old reply.

- [X] T012 [P] [US2] Add deterministic checks in `tests/api/test_web_chat.py` through the existing agent with stubbed Ollama and MCP. Assert exact tool names and fixture IDs for interleaved follow-ups in two conversations. Verify a `200` clarification reply when a fresh conversation lacks a fixture selection. Verify that multiple matches also return a `200` clarification and preserve any previously selected fixture. Verify that an unrelated `ValueError` follows the generic error path without exposing exception details. Also cover idempotent release, release during a pending turn, and shutdown cleanup.
- [X] T013 [P] [US2] Add explicit ambiguous-fixture and page-exit validation cases to `specs/001-add-agent-chat/quickstart.md`, including ambiguity from multiple matching fixtures and restoration via the browser Back control.
- [X] T014 [US2] Complete per-conversation state handling in `src/football_team_assistant/web_chat/conversations.py`. Reuse agent state across successful turns and keep it independent across conversations. Enforce “Tool records and selected fixture IDs are never accepted as conversation state from the browser.” Recognize the resolver's existing multiple-match `ValueError` by the fixed prefix specified in `specs/001-add-agent-chat/plan.md`, restore the pre-turn agent state, and return the clarification as an ordinary assistant reply. Keep other `ValueError` instances on the generic error path and preserve existing interfaces. Remove released entries, cancel their pending turns, and prevent late completions from publishing or restoring them.
- [X] T015 [P] [US2] Add the idempotent `DELETE /chat/conversations/{conversation_id}` release route in `src/football_team_assistant/web_chat/app.py`; return the contract's status for existing, released, and unknown IDs.
- [X] T016 [P] [US2] Handle `pagehide` and back-forward cache restoration in `src/football_team_assistant/web_chat/static/chat.js`. Release a departing page using keepalive, ignore its outstanding callbacks, and create a fresh conversation on reload, restore, or separate tab. Keep ordinary tab switches within the same conversation and keep transcripts in page memory.

**Checkpoint** — Tabs retain their own fixture context across turns and start fresh after reload.

## Phase 5 — User Story 3 · Recover from a failed reply (P3)

**Goal** — Preserve enough state for an informed retry after a bounded wait. Covers FR-004,
SC-004, and the restart clarification.

**Independent test** — Simulate unavailable and timed-out replies after a successful exchange.
Retry each without retyping and verify the earlier context survives. Restart the chat service
with the tab open and verify that the earlier transcript and failed question remain, with a
fresh-context notice before resending.

- [X] T017 [P] [US3] Add deterministic tests in `tests/api/test_web_chat.py` for timeouts, unavailable and empty replies, exception and cancellation rollback, retry after a failed turn, replay after an interrupted response, rejection of a retained ID reused with different normalized text, and a missing conversation after service restart. Assert that the `404 conversation_missing` response body does not echo the supplied conversation ID.
- [X] T018 [P] [US3] Prepare the recovery scenarios in `specs/001-add-agent-chat/quickstart.md` for the US3 checkpoint. Specify the test app's restart procedure and expected outcomes for keyboard-only retry and starting fresh, visible focus, announced notices, and fixture context after restart.
- [X] T019 [US3] Add replay in `src/football_team_assistant/web_chat/conversations.py` on top of T005's deadline and rollback. Keep only “the most recent successful UUID, normalized input, and reply” for replay. Release failed request IDs and enforce the contract for duplicate or conflicting submissions.
- [X] T020 [US3] Map a missing conversation to the documented `404 conversation_missing` response in `src/football_team_assistant/web_chat/app.py`, with an actionable plain-language message and no internal exception details.
- [X] T021 [US3] Add keyboard-operable manual retry after failures reported by T011 in `src/football_team_assistant/web_chat/static/chat.js`. Keep the original question and completed transcript visible and ensure “The retry of the current failed or unconfirmed turn keeps its UUID, while a new turn uses a fresh UUID.” Announce pending feedback and errors on retry. After a missing conversation, announce context loss before resending and require the coach to start fresh. Ensure the retry and start-fresh controls have visible keyboard focus.
- [X] T022 [US3] Add the documented `browser_test_app` factory to `tests/api/test_web_chat.py` with ordinary replies delayed by at least 500 ms and fail-once unavailable, timeout, and missing-response scenarios using shortened test deadlines.

**Checkpoint** — Transient failures can be retried in place, and a restart leaves the transcript
and failed question available with an explicit fresh-context notice.

## Phase 6 — Cross-cutting validation

- [X] T023 [P] Run Ruff lint and format checks from the repository root using the rules in `pyproject.toml`.
- [X] T024 [P] Run the chat boundary tests in `tests/api/test_web_chat.py` and compatibility regressions in `tests/api/test_app.py`, `tests/test_football_agent.py`, and `tests/test_squad_optimizer.py`. Run the complete suite when the isolated integration database is available and record any verification that could not run.
- [X] T025 [P] Build a wheel using `pyproject.toml` and verify it includes `src/football_team_assistant/web_chat/static/index.html`, `src/football_team_assistant/web_chat/static/chat.css`, and `src/football_team_assistant/web_chat/static/chat.js`. Confirm the installed chat app resolves its assets outside the repository root.
- [ ] T026 Run and record the browser acceptance and performance checks in `specs/001-add-agent-chat/quickstart.md`. Include the seeded isolated PostgreSQL and local Ollama workflow, 16-player squad timings, and pending feedback results for the 20-prompt workload at the 19-of-20 within 250 ms threshold.

## Dependencies and execution order

```text
Setup → Foundation → US1 (MVP) → US2 → US3 → Cross-cutting validation
```

- Setup establishes package and asset packaging. The foundation establishes the app, shared
  runtime, and conversation registry used by every story.
- US2 extends US1's chat and conversation routes. US3 builds on the same conversation state to
  restore or reset context on failure. Each story has a separate acceptance scenario.
- Write each story's boundary tests first and observe the expected failure before implementing
  the behavior. Finish each story's checkpoint before moving to the next.

### Parallel execution examples

| Phase | Tasks that can run together | When |
| --- | --- | --- |
| US1 | T006 HTTP tests and T007 quickstart | After the foundation |
| US1 | T008 page markup, T009 styles, and T010 routes | After T006–T007, with shared HTML/CSS selectors agreed. T011 integrates them. |
| US2 | T012 HTTP tests and T013 quickstart | After US1 |
| US2 | T015 release route and T016 browser lifecycle | After T014 defines release behavior |
| US3 | T017 recovery tests and T018 quickstart | After US2 |
| Cross-cutting | T023 Ruff, T024 regression tests, and T025 wheel validation | After US3 |

## Implementation strategy

1. Deliver the MVP through US1. Demonstrate a single browser question and reply on the host
   with responsive layout, keyboard access, and pending feedback.
2. Add US2 and demonstrate follow-ups with two independent tabs and fresh context after reload.
3. Add US3 and demonstrate transient recovery and restart recovery in an already-open tab.
4. Run the cross-cutting checks before treating the full feature as ready.

## Phase 7: Convergence

- [X] T027 Make the completed agent state and replay record commit together in `src/football_team_assistant/web_chat/conversations.py`. If the request is cancelled after the agent returns, preserve a replayable result or roll back before the next admission. Add a deterministic cancellation-at-completion regression in `tests/api/test_web_chat.py` and verify that retrying the same request never applies a turn twice per FR-004, T005, and T019 (contradicts).
- [ ] T028 Run the keyboard-only send, failure retry, and restart recovery scenarios at 360 and 1280 pixels with a native screen reader. Confirm audible pending, error, and fresh-context notices, then record the browser, screen reader, and results in `specs/001-add-agent-chat/quickstart.md` per SC-002 and T026 (partial).
- [ ] T029 From a second physical device on the same private network, verify that the chat page and conversation request cannot connect to the host LAN address while the local loopback app is running. Record both results in `specs/001-add-agent-chat/quickstart.md` per US1/AC3 and T026 (partial).
