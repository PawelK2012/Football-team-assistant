import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AsyncExitStack, asynccontextmanager
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, call
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from football_team_assistant.football_agent import FootballAgent
from football_team_assistant.web_chat import app as chat
from football_team_assistant.web_chat.conversations import Conversations
from tests.test_football_agent import TOOLS, mcp_result, model_response

ORIGIN = "http://127.0.0.1:8001"
HEADERS = {"Origin": ORIGIN}
CONVERSATIONS = "/chat/conversations"


class StubAgent:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.current_fixture_id: int | None = None

    async def ask(self, question: str) -> str:
        self.messages.append(question)
        return f"Reply to {question}"


def make_test_app(
    factory: Callable[[], StubAgent | FootballAgent] = StubAgent, **kwargs: float
) -> FastAPI:
    @asynccontextmanager
    async def runtime() -> AsyncIterator[chat.AgentFactory]:
        yield cast(chat.AgentFactory, factory)

    return chat.create_app(runtime=runtime, **kwargs)


def client_for(app: FastAPI) -> TestClient:
    return TestClient(app, base_url=ORIGIN, headers=HEADERS, client=("127.0.0.1", 12345))


def async_client_for(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345))
    return httpx.AsyncClient(base_url=ORIGIN, headers=HEADERS, transport=transport)


def turn_path(conversation_id: str) -> str:
    return f"{CONVERSATIONS}/{conversation_id}/turns"


def turn_data(message: object, request_id: str | None = None) -> dict[str, object]:
    return {"request_id": request_id or str(uuid4()), "message": message}


@pytest.fixture
def client() -> Iterator[TestClient]:
    with client_for(make_test_app()) as test_client:
        yield test_client


def test_page_assets_and_turn(client: TestClient) -> None:
    page = client.get("/chat")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    for asset in ("chat.css", "chat.js"):
        assert f"/chat/static/{asset}" in page.text
        assert client.get(f"/chat/static/{asset}").status_code == 200
    created = client.post(CONVERSATIONS)
    assert created.status_code == 201
    data = turn_data("  upcoming fixtures  ")
    reply = client.post(turn_path(created.json()["conversation_id"]), json=data)
    assert reply.json() == {"request_id": data["request_id"], "reply": "Reply to upcoming fixtures"}
    assert reply.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("request_kwargs", "status", "code"),
    [
        ({"json": turn_data("  ")}, 400, "invalid_request"),
        ({"json": turn_data("hello", "invalid")}, 400, "invalid_request"),
        ({"json": turn_data(123)}, 400, "invalid_request"),
        ({"json": {**turn_data("hello"), "fixture_id": 7}}, 400, "invalid_request"),
        ({"json": []}, 400, "invalid_request"),
        ({"content": "{", "headers": {"Content-Type": "application/json"}}, 400, "invalid_request"),
        ({"content": "secret"}, 415, "unsupported_content_type"),
    ],
)
def test_turn_validation(
    client: TestClient, request_kwargs: dict[str, object], status: int, code: str
) -> None:
    identifier = client.post(CONVERSATIONS).json()["conversation_id"]
    response = client.post(turn_path(identifier), **request_kwargs)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert identifier not in response.text
    assert "secret" not in response.text


def test_access_guard(client: TestClient) -> None:
    assert client.get("/chat", headers={"Host": "other.invalid"}).status_code == 403
    assert client.post(CONVERSATIONS, headers={"Origin": "http://other.invalid"}).status_code == 403
    assert client.post(CONVERSATIONS, headers={"Origin": ""}).status_code == 403
    assert client.get("/chat/static/chat.js", headers={"Host": "elsewhere"}).status_code == 403
    with TestClient(make_test_app(), base_url=ORIGIN, client=("192.0.2.10", 1234)) as remote:
        assert remote.get("/chat", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403
        assert remote.post(CONVERSATIONS, headers=HEADERS).status_code == 403


@pytest.mark.asyncio
async def test_overlapping_turn_is_rejected() -> None:
    started = asyncio.Event()
    finish = asyncio.Event()

    class SlowAgent(StubAgent):
        async def ask(self, question: str) -> str:
            started.set()
            await finish.wait()
            return await super().ask(question)

    agent = SlowAgent()
    app = make_test_app(lambda: agent)
    async with app.router.lifespan_context(app), async_client_for(app) as client:
        identifier = (await client.post(CONVERSATIONS)).json()["conversation_id"]
        path = turn_path(identifier)
        first = asyncio.create_task(client.post(path, json=turn_data("first")))
        await asyncio.wait_for(started.wait(), 2)
        try:
            second = await client.post(path, json=turn_data("second"))
            assert second.status_code == 409
            assert second.json()["error"]["code"] == "turn_pending"
        finally:
            finish.set()
            assert (await first).status_code == 200
        assert agent.messages == ["first"]


def test_stalled_turn_is_cancelled_and_rolled_back() -> None:
    cancelled = []

    class StalledAgent(StubAgent):
        async def ask(self, question: str) -> str:
            self.messages.append(question)
            self.current_fixture_id = 42
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)

    agent = StalledAgent()
    with client_for(make_test_app(lambda: agent, turn_timeout=0.01)) as client:
        identifier = client.post(CONVERSATIONS).json()["conversation_id"]
        response = client.post(turn_path(identifier), json=turn_data("stalled"))
        assert response.status_code == 504
        assert response.json()["error"]["code"] == "turn_timeout"
    assert cancelled == [True]
    assert agent.messages == []
    assert agent.current_fixture_id is None


@pytest.mark.parametrize("failed_step", ["initialize", "list_tools"])
def test_degraded_startup_still_serves_page(
    monkeypatch: pytest.MonkeyPatch, failed_step: str
) -> None:
    closed = []

    @asynccontextmanager
    async def stdio(*args: object, **kwargs: object) -> AsyncIterator[tuple[None, None]]:
        try:
            yield None, None
        finally:
            closed.append("stdio")

    @asynccontextmanager
    async def ollama() -> AsyncIterator[None]:
        try:
            yield None
        finally:
            closed.append("ollama")

    class Session:
        async def __aenter__(self) -> "Session":
            return self

        async def __aexit__(self, *args: object) -> None:
            closed.append("session")

        async def initialize(self) -> None:
            if failed_step == "initialize":
                raise RuntimeError("private backend details")

        async def list_tools(self) -> None:
            await asyncio.Future()

    monkeypatch.setattr(chat, "stdio_client", stdio)
    monkeypatch.setattr(chat, "AsyncClient", ollama)
    monkeypatch.setattr(chat, "ClientSession", lambda *_: Session())
    with client_for(chat.create_app(startup_timeout=0.01)) as client:
        assert closed == ["session", "stdio", "ollama"]
        assert client.get("/chat").status_code == 200
        response = client.post(CONVERSATIONS)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "agent_unavailable"
        assert "private" not in response.text


def test_fixture_followups_and_clarifications_use_independent_agents(
    sample_squads: dict,
) -> None:
    fixtures = [
        {"id": 6, "date": "2026-11-29", "opponent": "North Test FC", "home": True},
        {"id": 7, "date": "2026-11-30", "opponent": "South Test FC", "home": False},
    ]
    model = SimpleNamespace(chat=AsyncMock(return_value=model_response(content="Fixture lookup")))

    async def tool_result(name: str, arguments: dict[str, int]) -> SimpleNamespace:
        if name == "fixtures":
            return mcp_result(fixtures)
        if name == "generate_match_squads":
            fixture = next(row for row in fixtures if row["id"] == arguments["fixture_id"])
            return mcp_result({**sample_squads, "fixture": fixture})
        return mcp_result([])

    session = SimpleNamespace(call_tool=AsyncMock(side_effect=tool_result))

    def factory() -> FootballAgent:
        return FootballAgent(ollama=model, mcp_session=session, tools=TOOLS)

    with client_for(make_test_app(factory)) as client:
        north, south = [client.post(CONVERSATIONS).json()["conversation_id"] for _ in range(2)]

        def ask(identifier: str, text: str) -> httpx.Response:
            return client.post(turn_path(identifier), json=turn_data(text))

        unspecified = ask(north, "Who is available?")
        assert unspecified.status_code == 200
        assert "Which fixture do you mean?" in unspecified.json()["reply"]
        assert ask(north, "Who is available for North Test FC?").status_code == 200
        assert ask(south, "Who is available for South Test FC?").status_code == 200
        ambiguous = ask(north, "Who is available for North Test FC or South Test FC?")
        assert ambiguous.status_code == 200
        assert "Multiple fixtures match" in ambiguous.json()["reply"]
        for identifier, opponent in ((south, "South Test FC"), (north, "North Test FC")):
            squads = ask(identifier, "Create squads for that game")
            assert squads.status_code == 200
            assert f"Fixture: {opponent}" in squads.json()["reply"]
        unrelated = ask(north, "Who is available for fixture 999?")
        assert unrelated.status_code == 503
        assert "999" not in unrelated.text

    assert session.call_tool.await_args_list == [
        call("fixtures", arguments={}),
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 6}),
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 7}),
        call("fixtures", arguments={}),
        call("fixtures", arguments={}),
        call("generate_match_squads", arguments={"fixture_id": 7}),
        call("fixtures", arguments={}),
        call("generate_match_squads", arguments={"fixture_id": 6}),
        call("fixtures", arguments={}),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("shutdown", [False, True])
async def test_release_or_shutdown_cancels_pending_turn(shutdown: bool) -> None:
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class PendingAgent(StubAgent):
        async def ask(self, question: str) -> str:
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

    app = make_test_app(PendingAgent)
    async with AsyncExitStack() as lifespan, async_client_for(app) as client:
        await lifespan.enter_async_context(app.router.lifespan_context(app))
        identifier = (await client.post(CONVERSATIONS)).json()["conversation_id"]
        release_path = f"{CONVERSATIONS}/{identifier}"
        pending = asyncio.create_task(client.post(turn_path(identifier), json=turn_data("first")))
        try:
            await asyncio.wait_for(started.wait(), 2)
            if shutdown:
                await lifespan.aclose()
            else:
                assert (await client.delete(release_path)).status_code == 204
                assert (await client.delete(release_path)).status_code == 204
                assert (await client.delete(f"{CONVERSATIONS}/unknown")).status_code == 204
            assert (await asyncio.wait_for(pending, 2)).status_code == 404
            assert cancelled.is_set()
            assert (
                await client.post(turn_path(identifier), json=turn_data("late"))
            ).status_code == 404
        finally:
            await lifespan.aclose()
            await asyncio.gather(pending, return_exceptions=True)


@pytest.mark.parametrize("failure", ["exception", "empty", "timeout"])
def test_retry_uses_rolled_back_context_and_only_latest_success_is_replayed(failure: str) -> None:
    class FailingAgent(StubAgent):
        attempts = 0

        async def ask(self, question: str) -> str:
            self.attempts += 1
            if self.attempts == 2:
                self.current_fixture_id = 99
                self.messages.append("incomplete private state")
                if failure == "exception":
                    raise RuntimeError("private backend error")
                if failure == "timeout":
                    await asyncio.Future()
                return " "
            if self.attempts == 1:
                self.current_fixture_id = 6
            assert self.current_fixture_id == 6
            return await super().ask(question)

    agent = FailingAgent()
    with client_for(make_test_app(lambda: agent, turn_timeout=0.01)) as client:
        identifier = client.post(CONVERSATIONS).json()["conversation_id"]
        path = turn_path(identifier)
        assert client.post(path, json=turn_data("North Test FC")).status_code == 200
        retry = turn_data("Who's available?")
        failed = client.post(path, json=retry)
        assert failed.status_code == (504 if failure == "timeout" else 503)
        assert "private" not in failed.text
        assert agent.messages == ["North Test FC"]
        assert agent.current_fixture_id == 6
        succeeded = client.post(path, json=retry)
        assert succeeded.status_code == 200
        normalized = {**retry, "message": "  Who's available?  "}
        assert client.post(path, json=normalized).json() == succeeded.json()
        assert agent.attempts == 3
        conflict = client.post(path, json={**retry, "message": "different"})
        assert conflict.status_code == 400
        assert conflict.json()["error"]["code"] == "invalid_request"
        assert agent.attempts == 3

        assert client.post(path, json=turn_data("new turn")).status_code == 200
        assert client.post(path, json=retry).status_code == 200
        assert agent.attempts == 5


@pytest.mark.asyncio
async def test_cancellation_at_turn_completion_preserves_replay() -> None:
    class CompletingAgent(StubAgent):
        async def ask(self, question: str) -> str:
            reply = await super().ask(question)
            self.current_fixture_id = 6
            if len(self.messages) == 1:
                # Cancel the caller before it can resume with the agent task's reply.
                asyncio.get_running_loop().call_soon(request.cancel)
            return reply

    agent = CompletingAgent()
    conversations = Conversations(lambda: cast(FootballAgent, agent), timeout=1)
    identifier = conversations.create()
    request_id = str(uuid4())
    question = "Who is available for North Test FC?"
    request = asyncio.create_task(conversations.turn(identifier, request_id, question))
    try:
        with pytest.raises(asyncio.CancelledError):
            await request

        reply = await conversations.turn(identifier, request_id, question)
        assert reply == f"Reply to {question}"
        assert agent.messages == [question]
        assert agent.current_fixture_id == 6
    finally:
        await conversations.close()


def test_restart_invalidates_conversation_without_echoing_identifier() -> None:
    app = make_test_app()
    with client_for(app) as client:
        identifier = client.post(CONVERSATIONS).json()["conversation_id"]
    with client_for(app) as client:
        response = client.post(turn_path(identifier), json=turn_data("the last question"))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "conversation_missing"
        assert identifier not in response.text
        assert "the last question" not in response.text
        fresh = client.post(CONVERSATIONS).json()["conversation_id"]
        assert fresh != identifier


class BrowserAgent(StubAgent):
    def __init__(self) -> None:
        super().__init__()
        self.triggered_failures: set[str] = set()

    async def ask(self, question: str) -> str:
        if question not in self.triggered_failures:
            if question == "Simulate unavailable":
                self.triggered_failures.add(question)
                raise RuntimeError("simulated unavailable")
            if question == "Simulate timeout":
                self.triggered_failures.add(question)
                await asyncio.Future()

        await asyncio.sleep(0.5)
        self.messages.append(question)
        if "North Test FC" in question:
            self.current_fixture_id = 6
        elif "South Test FC" in question:
            self.current_fixture_id = 7

        if question == "Which fixtures are upcoming?":
            return "Upcoming fixtures: North Test FC and South Test FC."
        if question == "Simulate markup":
            return "<strong>Plain text</strong> " + "wrap" * 80
        fixture = {6: "North Test FC", 7: "South Test FC"}.get(self.current_fixture_id)
        if fixture is None:
            return "Which fixture do you mean? Please specify a fixture ID or opponent."
        return f"Fixture: {fixture}\nCoach asked: {question}"


def browser_test_app() -> FastAPI:
    """Run deterministic browser checks without Ollama or PostgreSQL."""
    app = make_test_app(BrowserAgent, turn_timeout=1.2)
    delayed_responses: set[str] = set()

    @app.middleware("http")
    async def simulate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        turn = None
        if request.method == "POST" and request.url.path.endswith("/turns"):
            try:
                turn = await request.json()
            except ValueError:
                pass
        response = await call_next(request)
        if response.status_code != 200:
            return response
        if request.url.path == "/chat/static/chat.js":
            script = (chat.STATIC / "chat.js").read_text().replace("95_000", "3_000", 1)
            return Response(
                script, media_type="text/javascript", headers={"Cache-Control": "no-store"}
            )
        if isinstance(turn, dict) and turn.get("message") == "Simulate missing response":
            request_id = turn["request_id"]
            if request_id not in delayed_responses:
                delayed_responses.add(request_id)
                await asyncio.sleep(4)
        return response

    return app
