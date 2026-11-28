# Research — Football Agent Web Chat

## Separate loopback web app

**Decision** — Add a dedicated FastAPI/Uvicorn app for the chat. Serve plain browser assets
and same-origin JSON routes. Bind to `127.0.0.1:8001` with one worker and disable proxy headers
and access logs.
Validate the actual loopback peer and canonical Host on all chat requests. Require the canonical
Origin on conversation writes and provide no cross-origin browser access.

**Rationale** — The current FastAPI app serves fixtures, availability, squads, and health.
The current agent runs through a CLI with its own MCP and Ollama setup. A separate app prevents
chat routes, startup, or upstream failures from affecting existing callers. FastAPI supports
serving static assets using dependencies already present. [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/) · [Uvicorn binding and proxy settings](https://uvicorn.dev/settings/)

**Alternatives considered** — Adding routes to the existing FastAPI app changes the published
route surface and makes local-only access depend on that app's deployment. A separate frontend
dev server adds a build and proxy workflow.

## Conversation transport and isolation

**Decision** — Use JSON over HTTP with one unpredictable, server-issued conversation ID per loaded
page. Hold it only in page memory. Keep an agent per conversation in a single-process registry.
On `pagehide`, invalidate the page's pending callbacks and send a bodyless keepalive DELETE.
Reset the page if the browser restores it from its back-forward cache. Release all conversations
on shutdown. [Fetch keepalive](https://fetch.spec.whatwg.org/#request-keepalive-flag) · [HTML page transition events](https://html.spec.whatwg.org/multipage/nav-history-apis.html#the-pagetransitionevent-interface)

**Rationale** — `FootballAgent` holds model history and the selected fixture in mutable
instance state. Separate instances isolate tabs. HTTP allows a retry after a request connection
fails without coupling the agent state to one connection. A fresh page receives a fresh ID.

**Alternatives considered** — One shared agent mixes tabs. An agent per request loses
follow-ups. A socket per page ties the state to transport uptime. A database-backed registry
would introduce saved conversation history. Using a visibility event for cleanup would also
end conversations when a coach switches tabs.

## Agent lifecycle and failure recovery

**Decision** — The chat app lifespan opens and closes the Ollama client and stdio MCP session.
Launch the existing MCP module with the active Python interpreter and reuse the CLI's tool
conversion. Pass `DATABASE_URL` explicitly when set because stdio inherits a limited set of
environment variables. Bound MCP initialization and tool discovery together to 10 seconds.
Keep the page available if MCP startup fails and return an unavailable message asking the
coach to restart the chat service after fixing its configuration. A running conversation
can retry after a transient Ollama or tool error. A broken MCP subprocess requires restart.
Keep admission and rollback inside the chat adapter.

**Rationale** — The existing `ask()` rolls back an MCP tool timeout. Other failures, empty
replies, and cancellation require adapter-level rollback. The adapter checkpoints the
history length and selected fixture before an exclusive turn and restores both before
accepting another turn. Existing MCP tools read football data or compute squads, so an
abandoned upstream call has no database writes to reverse. The installed MCP version
successfully discovered all three tools with the active interpreter. [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/) · [Python cancellation and deadlines](https://docs.python.org/3.12/library/asyncio-task.html#timeouts)

**Alternatives considered** — Launching MCP on every turn adds repeated startup cost.
Changing CLI orchestration or adding an agent framework broadens the feature.

## Browser feedback and timeout

**Decision** — Show pending feedback before starting the request. Render messages using
`textContent`, preserve line breaks, and wrap long text. Use a 90-second server turn deadline,
a 95-second browser fallback, a separate 10-second conversation creation deadline, and
manual retry. Validate the feedback target separately from live model timing.

**Rationale** — The chat should respond immediately to the coach's action even when the local
model is busy. A server deadline bounds work independently of a browser fetch abort. The
fixed initial values give implementation and tests a concrete starting point. Calibrate
the live budget against recorded fixture and squad timings, including cold model startup and
a 16-player roster, before changing it. Measure the first rendered pending frame with the
browser performance timeline. [DOM Standard](https://dom.spec.whatwg.org/#dom-node-textcontent) · [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)

**Alternatives considered** — Streaming adds a partial-response state to the UI and adapter.
Automatic retries make it harder to reason about duplicate work and failure recovery.
