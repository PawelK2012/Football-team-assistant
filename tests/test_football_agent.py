from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

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
        {"id": 1, "name": "Henry", "rating": 4.5},
        {"id": 13, "name": "Cuan", "rating": 3.5},
        {"id": 14, "name": "Leo", "rating": 5.0},
    ]

    agent.ollama.chat.side_effect = [
        model_response(tool_call("fixtures")),
        model_response(tool_call("available_players", fixture_id=6)),
    ]

    agent.mcp_session.call_tool.side_effect = [
        mcp_result(fixtures),
        mcp_result(players),
    ]

    answer = await agent.ask("Who is available for the next match?")

    assert "1. Henry (4.5)" in answer
    assert "2. Cuan (3.5)" in answer
    assert "3. Leo (5.0)" in answer

    assert answer.count("Henry") == 1
    assert answer.count("Cuan") == 1

    assert agent.mcp_session.call_tool.await_count == 2


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
        model_response(tool_call("fixtures")),
        model_response(tool_call("generate_match_squads", fixture_id=6)),
    ]

    agent.mcp_session.call_tool.side_effect = [
        mcp_result(fixtures),
        mcp_result(sample_squads),
    ]

    answer = await agent.ask("Generate two balanced squads for Verona FC")

    assert "Squad A" in answer
    assert "Squad B" in answer

    assert answer.count("Henry") == 1
    assert answer.count("Sam") == 1

    assert "Goalkeeper: Jack" in answer
    assert "Goalkeeper: Tom" in answer

    assert agent.mcp_session.call_tool.await_count == 2


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
    agent.ollama.chat.return_value = model_response(
        tool_call("available_players", fixture_id="six")
    )

    with pytest.raises(ValueError, match="Invalid arguments"):
        await agent.ask("Who is available?")

    agent.mcp_session.call_tool.assert_not_awaited()
