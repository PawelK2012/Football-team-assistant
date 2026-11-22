import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest

from football_team_assistant.fixture_resolution import (
    extract_explicit_fixture_id,
)
from football_team_assistant.football_agent import FootballAgent

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": "",
            "parameters": {
                "type": "object",
                "properties": ({} if name == "fixtures" else {"fixture_id": {"type": "integer"}}),
                "required": ([] if name == "fixtures" else ["fixture_id"]),
            },
        },
    }
    for name in (
        "fixtures",
        "available_players",
        "generate_match_squads",
    )
]


def tool_call(name, **arguments):
    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        )
    )


def model_response(*calls, content=""):
    return SimpleNamespace(
        message=SimpleNamespace(
            content=content,
            tool_calls=list(calls),
        )
    )


def mcp_result(data):
    return SimpleNamespace(
        is_error=False,
        structured_content={"result": data},
        content=[],
    )


@pytest.fixture
def agent():
    ollama = SimpleNamespace(chat=AsyncMock())
    session = SimpleNamespace(call_tool=AsyncMock())

    return FootballAgent(
        ollama=ollama,
        mcp_session=session,
        tools=TOOLS,
    )


@pytest.mark.asyncio
async def test_availability_uses_exact_tool_data(agent):
    fixtures = [
        {
            "id": 6,
            "date": "2026-11-08",
            "opponent": "Verona FC",
            "home": True,
        }
    ]

    players = [
        {"id": 1, "name": "MrX", "rating": 4.5},
        {"id": 13, "name": "MrY", "rating": 3.5},
        {"id": 14, "name": "Orangutan", "rating": 5.0},
    ]

    agent.ollama.chat.side_effect = [
        model_response(tool_call("available_players", fixture_id=6)),
    ]

    agent.mcp_session.call_tool.side_effect = [
        mcp_result(fixtures),
        mcp_result(players),
    ]

    answer = await agent.ask("Who is available for fixture 6?")

    assert "1. MrX (4.5)" in answer
    assert "2. MrY (3.5)" in answer
    assert "3. Orangutan (5.0)" in answer

    assert answer.count("MrX") == 1
    assert answer.count("MrY") == 1

    assert agent.mcp_session.call_tool.await_count == 2


@pytest.fixture(params=[False, True], ids=["model-call", "fallback"])
def availability_agent(agent: FootballAgent, request: pytest.FixtureRequest) -> FootballAgent:
    if request.param:
        agent.ollama.chat.return_value = model_response()
    else:
        agent.ollama.chat.return_value = model_response(
            tool_call("available_players", fixture_id=6)
        )
    return agent


@pytest.fixture
def availability_fixtures() -> list[dict]:
    return [{"id": 6, "date": "2026-11-08", "opponent": "Verona FC", "home": True}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, expected_error",
    [
        pytest.param({"status": "unexpected"}, "expected a list", id="not-a-list"),
        pytest.param(["MrX"], "expected a player record", id="not-a-player-record"),
        pytest.param([{"rating": 4.5}], "missing name", id="missing-name"),
        pytest.param([{"name": "MrX"}], "missing rating", id="missing-rating"),
    ],
)
async def test_availability_rejects_malformed_tool_result(
    availability_agent: FootballAgent,
    availability_fixtures: list[dict],
    payload: object,
    expected_error: str,
) -> None:
    availability_agent.mcp_session.call_tool.side_effect = [
        mcp_result(availability_fixtures),
        mcp_result(payload),
    ]
    with pytest.raises(ValueError, match=f"available_players.*{expected_error}"):
        await availability_agent.ask("Who is available for fixture 6?")

    assert not any(
        isinstance(message, dict)
        and message.get("role") == "tool"
        and message.get("tool_name") == "available_players"
        for message in availability_agent.messages
    )


@pytest.mark.asyncio
async def test_availability_accepts_empty_player_list(
    availability_agent: FootballAgent, availability_fixtures: list[dict]
) -> None:
    availability_agent.mcp_session.call_tool.side_effect = [
        mcp_result(availability_fixtures),
        mcp_result([]),
    ]

    answer = await availability_agent.ask("Who is available for fixture 6?")

    assert answer.strip() == "Available players (0):"


@pytest.mark.asyncio
async def test_availability_tool_times_out(
    availability_agent: FootballAgent,
    availability_fixtures: list[dict],
) -> None:
    availability_agent.tool_timeout_seconds = 0.01
    stalled = asyncio.Event()

    async def call_tool(name: str, *, arguments: dict) -> SimpleNamespace:
        if name == "fixtures":
            return mcp_result(availability_fixtures)
        await stalled.wait()
        return mcp_result([])

    availability_agent.mcp_session.call_tool.side_effect = call_tool

    with pytest.raises(TimeoutError, match="MCP tool 'available_players' timed out"):
        await asyncio.wait_for(availability_agent.ask("Who is available for fixture 6?"), 1)

    assert availability_agent.mcp_session.call_tool.await_args_list == [
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 6}),
    ]
    assert not any(
        isinstance(message, dict) and message.get("role") == "tool"
        for message in availability_agent.messages
    )


@pytest.mark.asyncio
async def test_fixture_lookup_times_out_before_calling_ollama(agent: FootballAgent) -> None:
    agent.tool_timeout_seconds = 0.01
    stalled = asyncio.Event()

    async def call_tool(name: str, *, arguments: dict) -> SimpleNamespace:
        await stalled.wait()
        return mcp_result([])

    agent.mcp_session.call_tool.side_effect = call_tool

    with pytest.raises(TimeoutError, match="MCP tool 'fixtures' timed out"):
        await asyncio.wait_for(agent.ask("Who is available for fixture 6?"), 1)

    agent.mcp_session.call_tool.assert_awaited_once_with("fixtures", arguments={})
    agent.ollama.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_squad_generation_uses_exact_tool_data(
    agent,
    sample_squads,
):
    fixtures = [
        {
            "id": 6,
            "date": "2026-11-08",
            "opponent": "Verona FC",
            "home": True,
        }
    ]

    agent.ollama.chat.side_effect = [
        model_response(tool_call("generate_match_squads", fixture_id=6)),
    ]

    agent.mcp_session.call_tool.side_effect = [
        mcp_result(fixtures),
        mcp_result(sample_squads),
    ]

    answer = await agent.ask("Generate two balanced squads for Verona FC")

    assert "Squad A" in answer
    assert "Squad B" in answer

    assert answer.count("MrX") == 1
    assert answer.count("Orangutan") == 1

    assert "Goalkeeper: Johny" in answer
    assert "Goalkeeper: Diebre" in answer

    assert agent.mcp_session.call_tool.await_count == 2

    assert "3. Orangutan (6.0) (GK)" in answer
    assert "1. MBape (6.0) (GK)" in answer


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected(agent):
    agent.ollama.chat.return_value = model_response(tool_call("delete_all_players"))

    with pytest.raises(ValueError, match="Unknown tool"):
        await agent.ask("Delete all players")

    agent.mcp_session.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_mcp_error_is_propagated(agent):
    agent.ollama.chat.return_value = model_response(tool_call("available_players", fixture_id=6))

    agent.mcp_session.call_tool.return_value = SimpleNamespace(
        is_error=True,
        structured_content=None,
        content=[
            SimpleNamespace(
                type="text",
                text="Database connection failed",
            )
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="Database connection failed",
    ):
        await agent.ask("Who is available?")


@pytest.mark.asyncio
async def test_agent_iteration_limit(agent, monkeypatch):
    monkeypatch.setattr(
        "football_team_assistant.football_agent.MAX_TOOL_ITERATIONS",
        3,
    )

    agent.ollama.chat.return_value = model_response(tool_call("fixtures"))

    agent.mcp_session.call_tool.return_value = mcp_result([])

    with pytest.raises(
        RuntimeError,
        match="exceeded 3 iterations",
    ):
        await agent.ask("Find fixtures")

    assert agent.ollama.chat.await_count == 3


@pytest.mark.asyncio
async def test_invalid_arguments_never_reach_mcp(agent):
    fixtures = [
        {
            "id": 6,
            "date": "2026-11-08",
            "opponent": "Verona FC",
            "home": True,
        }
    ]

    agent.mcp_session.call_tool.return_value = mcp_result(fixtures)

    agent.ollama.chat.return_value = model_response(
        tool_call(
            "available_players",
            fixture_id="six",
            unexpected_argument=True,
        )
    )

    with pytest.raises(ValueError, match="Invalid arguments"):
        await agent.ask("Who is available for fixture 6?")

    # Fixture discovery is allowed, but invalid tool execution isn't.
    assert agent.mcp_session.call_tool.await_count == 1
    assert agent.mcp_session.call_tool.await_args.args[0] == "fixtures"


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Who is available for fixture 6?", 6),
        ("Generate squads for fixture ID 7", 7),
        ("Show fixture #12", 12),
        ("Generate squads", None),
        ("Who is available?", None),
        ("We have 14 players", None),
    ],
)
def test_extract_explicit_fixture_id(question, expected):
    assert extract_explicit_fixture_id(question) == expected
