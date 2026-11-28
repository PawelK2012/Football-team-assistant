# Implementation Plan: Football Agent Web Chat

**Branch**: `introduced-chat-ui` | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-add-agent-chat/spec.md`.

## Summary

Add a single responsive chat page using plain HTML, CSS, and JavaScript. Serve it and its
JSON endpoints from a dedicated FastAPI app on the host computer. The app adapts the existing
`FootballAgent` to a browser and keeps each page's conversation in memory. A coach can ask
follow-up questions and retry transient failures with their prior fixture context intact.
After a service restart, the open tab retains the transcript and failed question and explains
that resending starts with fresh fixture context.

## Technical Context

- **Languages** — Python 3.12+, HTML, CSS, and browser JavaScript.
- **Dependencies** — The lockfile already provides FastAPI, Uvicorn, Ollama, and MCP. Use
  browser-native HTML, CSS, and JavaScript with these existing Python dependencies.
- **Storage** — Page memory for the visible transcript and process memory for agent state.
  Football data continues through existing MCP tools and PostgreSQL.
- **Testing** — pytest, pytest-asyncio, FastAPI TestClient, Ruff, and manual browser checks.
  Stub the model and MCP for deterministic tests. Use seeded, isolated data for live checks.
- **Project type and deployment** — A local ASGI web app with one Uvicorn worker bound to
  IPv4 loopback on port 8001. The chat page and its JSON endpoints share one origin.
- **Performance** — At least 19 of 20 submissions show pending feedback within 250 ms.
  Set an initial 90-second server deadline for a complete chat turn, with the existing
  10-second MCP per-call timeout. The browser stops waiting after 95 seconds if no response
  arrives. Conversation creation has a separate 10-second browser deadline. Enforce these
  deadlines in the browser chat MVP. Record live timings locally, including squad generation
  with 16 players.
- **Scope** — One coach on the host computer, isolated tabs, and one in-flight turn per
  conversation. Sign-in and administration are future features.

## Constitution Check

| Gate | Before research | After design |
| --- | --- | --- |
| I. Code quality and clear boundaries | Reuse the agent and tools. | The new HTTP adapter owns browser session state and delegates turns to the agent. Support code remains within the chat package and follows repository type hints and Ruff rules. |
| II. Deterministic testing and integration coverage | Exercise the added browser boundary. | Run the new HTTP boundary checks with controlled agent or Ollama/MCP stubs, including exact tool arguments for a fixture follow-up. Verify route access, MCP startup failure and discovery timeout, cancellation, retry, shutdown, and existing API and agent regressions. Live PostgreSQL checks use isolated data. |
| III. Consistent coach experience | Preserve existing agent behavior and interfaces. | Browser users receive the agent's reply or clarification verbatim. Chat-specific failures use stable error codes and plain language. Existing apps and protocol contracts require no changes or approvals. |
| IV. Measurable performance and bounded execution | Use the spec's feedback target and define a turn budget. | The quickstart specifies the timing workload, local environment, maximum roster, and timeout/failure checks. The existing execution path stays intact. |
| Technical constraints and workflow | Preserve local operation and review compatibility. | Ollama stays local. Chat requests share a loopback-only origin. Logs omit prompts, reply text, conversation IDs, and player data. The agent retains its existing tool argument validation. |

Both checks pass. The design adds a dedicated browser API and requires no existing API
change or constitution exception.

## Design and verification

1. Serve the page and conversation routes from the chat app. Verify the loopback peer,
   canonical Host, and write Origin at the HTTP boundary.
2. Own the Ollama client and stdio MCP session in the application's lifespan. Use the
   existing tool schema conversion and one agent instance per conversation. Keep turn
   admission, timeout, rollback, and replay in the conversation adapter. See the
   [data model](data-model.md) for state transitions and [research](research.md) for tool
   connection and recovery decisions. In the chat adapter, recognize the fixture resolver's
   existing `ValueError` by the fixed prefix `Multiple fixtures match. Please specify a fixture ID: `.
   Restore the pre-turn agent state and return that clarification as an ordinary assistant
   reply. Route other `ValueError` instances through generic error handling. Keep the
   resolver and existing agent interfaces intact.
3. Use text-only rendering, a labeled composer, and keyboard-operable send, retry, and
   fresh-context controls with visible focus. Announce pending, error, and fresh-context
   notices. Release a departing page's context when notified and treat a restored page
   as a fresh conversation.
4. Use the [browser contract](contracts/browser-chat.md) for HTTP integration checks
   and the [quickstart](quickstart.md) for the browser and performance checks. Cover
   fixture lookup and follow-ups (SC-001), narrow and keyboard use (SC-002), submission
   feedback timing (SC-003), and retry after unavailable and timeout responses (SC-004).

## Project Structure

### Documentation (this feature)

```text
specs/001-add-agent-chat/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── browser-chat.md
```

### Source Code (repository root)

```text
src/football_team_assistant/
├── api/                       # Existing HTTP app and endpoints
├── football_agent.py          # Existing agent entry point
├── mcp_agent.py               # Existing CLI
└── web_chat/                  # Proposed package
    ├── app.py                 # Loopback checks, assets, and JSON routes
    ├── conversations.py       # Agent lifecycle and per-page conversation state
    └── static/
        ├── index.html
        ├── chat.css
        └── chat.js

tests/
├── api/
│   ├── test_app.py            # Existing HTTP regression checks
│   └── test_web_chat.py        # Proposed HTTP boundary and lifecycle checks
└── test_football_agent.py     # Existing agent regression checks
```

**Structure decision** — Keep the feature inside the existing Python project with a separate
ASGI app. Resolve packaged assets relative to the module so startup works from any directory.
Include those assets in the Python distribution. Keep the browser UI, request validation,
and conversation lifecycle distinct so a future authenticated surface can reuse the agent.
