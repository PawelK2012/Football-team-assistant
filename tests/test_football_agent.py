import asyncio
import logging
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
    "question, model_replies, expected_tool_calls, expected_answer",
    [
        pytest.param(
            "Who is available for fixture 6?",
            [model_response(tool_call("available_players", fixture_id=999))],
            [("fixtures", {}), ("available_players", {"fixture_id": 6})],
            "Available players (2):\n\n1. Alex (4.5)\n2. Sam (3.5)",
            id="wrong-model-fixture-id",
        ),
        pytest.param(
            "Who is available for fixture 6?",
            [model_response(content="Taylor is available and has a rating of 5.0.")],
            [("fixtures", {}), ("available_players", {"fixture_id": 6})],
            "Available players (2):\n\n1. Alex (4.5)\n2. Sam (3.5)",
            id="python-fallback",
        ),
        pytest.param(
            "Who is available?",
            [],
            [("fixtures", {})],
            "Which fixture do you mean? Please specify a fixture ID or opponent.",
            id="no-fixture-selected",
        ),
    ],
)
async def test_availability_evaluation(
    agent: FootballAgent,
    availability_fixtures: list[dict],
    question: str,
    model_replies: list[SimpleNamespace],
    expected_tool_calls: list[tuple[str, dict[str, int]]],
    expected_answer: str,
) -> None:
    fixtures = [
        *availability_fixtures,
        {"id": 7, "date": "2026-11-15", "opponent": "Portmanock FC", "home": False},
    ]
    players = [
        {"id": 1, "name": "Alex", "rating": 4.5},
        {"id": 2, "name": "Sam", "rating": 3.5},
    ]
    agent.ollama.chat.side_effect = model_replies
    agent.mcp_session.call_tool.side_effect = [mcp_result(fixtures), mcp_result(players)]

    answer = await agent.ask(question)

    assert agent.mcp_session.call_tool.await_args_list == [
        call(name, arguments=arguments) for name, arguments in expected_tool_calls
    ]
    assert agent.ollama.chat.await_count == len(model_replies)
    assert answer == expected_answer


@pytest.mark.asyncio
async def test_availability_logs_correlate_model_and_mcp_by_turn(
    agent: FootballAgent,
    availability_fixtures: list[dict],
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent.ollama.chat.side_effect = [
        model_response(tool_call("available_players", fixture_id=6)),
        model_response(),
    ]
    fixtures = mcp_result(availability_fixtures)
    players = mcp_result([{"name": "Alex", "rating": 4.5}])
    agent.mcp_session.call_tool.side_effect = [fixtures, players, fixtures, players]
    logger_name = FootballAgent.__module__

    with caplog.at_level(logging.INFO, logger=logger_name):
        await agent.ask("Who is available for fixture 6?")
        await agent.ask("Who is available now?")

    records = [record for record in caplog.records if record.name == logger_name]
    assert len(records) == 6
    for turn_records, expected_tool_call_count in ((records[:3], 1), (records[3:], 0)):
        fixture_lookup, model_decision, availability_lookup = turn_records
        assert (fixture_lookup.tool_name, fixture_lookup.outcome) == (
            "fixtures",
            "response_received",
        )
        assert (availability_lookup.tool_name, availability_lookup.outcome) == (
            "available_players",
            "response_received",
        )
        assert all(record.levelno == logging.INFO for record in turn_records)
        assert model_decision.tool_call_count == expected_tool_call_count
        assert fixture_lookup.duration_ms >= 0
        assert availability_lookup.duration_ms >= 0
        assert model_decision.turn_id
        assert fixture_lookup.turn_id == model_decision.turn_id == availability_lookup.turn_id

    assert records[0].turn_id != records[3].turn_id


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
async def test_availability_timeout_preserves_completed_turns(
    availability_agent: FootballAgent,
    availability_fixtures: list[dict],
    caplog: pytest.LogCaptureFixture,
) -> None:
    availability_agent.tool_timeout_seconds = 0.01
    failed_response = availability_agent.ollama.chat.return_value
    failed_response.message.content = "Alice is available"
    availability_agent.ollama.chat.side_effect = [
        model_response(content="Hello, coach"),
        failed_response,
        model_response(content="How can I help?"),
    ]
    assert await availability_agent.ask("Hello") == "Hello, coach"
    completed_history = list(availability_agent.messages)

    stalled = asyncio.Event()

    async def call_tool(name: str, *, arguments: dict) -> SimpleNamespace:
        if name == "fixtures":
            return mcp_result(availability_fixtures)
        await stalled.wait()
        return mcp_result([])

    availability_agent.mcp_session.call_tool.side_effect = call_tool

    logger_name = FootballAgent.__module__
    with caplog.at_level(logging.INFO, logger=logger_name):
        with pytest.raises(TimeoutError, match="MCP tool 'available_players' timed out"):
            await asyncio.wait_for(availability_agent.ask("Who is available for fixture 6?"), 1)

    records = [record for record in caplog.records if record.name == logger_name]
    fixture_lookup, model_decision, timeout = records
    assert fixture_lookup.tool_name == "fixtures"
    assert model_decision.tool_call_count == len(failed_response.message.tool_calls)
    assert (timeout.levelno, timeout.tool_name, timeout.outcome) == (
        logging.WARNING,
        "available_players",
        "timeout",
    )
    assert timeout.turn_id
    assert fixture_lookup.turn_id == model_decision.turn_id == timeout.turn_id

    assert availability_agent.mcp_session.call_tool.await_args_list == [
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 6}),
    ]
    assert availability_agent.messages == completed_history

    assert await availability_agent.ask("What did you find?") == "How can I help?"
    follow_up_messages = availability_agent.ollama.chat.await_args.kwargs["messages"]
    assert follow_up_messages[: len(completed_history)] == completed_history
    assert follow_up_messages[len(completed_history)] == {
        "role": "user",
        "content": "What did you find?",
    }
    assert failed_response.message not in follow_up_messages


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "switch_times_out, expected_fixture_id",
    [
        pytest.param(True, 6, id="timed-out-switch"),
        pytest.param(False, 7, id="successful-switch"),
    ],
)
async def test_follow_up_uses_last_completed_fixture_selection(
    availability_agent: FootballAgent,
    availability_fixtures: list[dict],
    switch_times_out: bool,
    expected_fixture_id: int,
) -> None:
    fixtures = mcp_result(
        [
            *availability_fixtures,
            {"id": 7, "date": "2026-11-15", "opponent": "Portmanock FC", "home": True},
        ]
    )
    availability = mcp_result([])
    availability_agent.mcp_session.call_tool.side_effect = [
        fixtures,
        availability,
        fixtures,
        TimeoutError() if switch_times_out else availability,
        fixtures,
        availability,
    ]

    await availability_agent.ask("Who is available for fixture 6?")
    if switch_times_out:
        with pytest.raises(TimeoutError, match="MCP tool 'available_players' timed out"):
            await availability_agent.ask("Who is available for fixture 7?")
    else:
        await availability_agent.ask("Who is available for fixture 7?")
    await availability_agent.ask("Who is available now?")

    assert availability_agent.mcp_session.call_tool.await_args_list == [
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 6}),
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": 7}),
        call("fixtures", arguments={}),
        call("available_players", arguments={"fixture_id": expected_fixture_id}),
    ]


@pytest.mark.asyncio
async def test_fixture_lookup_times_out_before_calling_ollama(
    agent: FootballAgent, caplog: pytest.LogCaptureFixture
) -> None:
    agent.tool_timeout_seconds = 0.01
    completed_history = list(agent.messages)
    stalled = asyncio.Event()

    async def call_tool(name: str, *, arguments: dict) -> SimpleNamespace:
        await stalled.wait()
        return mcp_result([])

    agent.mcp_session.call_tool.side_effect = call_tool

    logger_name = FootballAgent.__module__
    with caplog.at_level(logging.INFO, logger=logger_name):
        with pytest.raises(TimeoutError, match="MCP tool 'fixtures' timed out"):
            await asyncio.wait_for(agent.ask("Who is available for fixture 6?"), 1)

    agent.mcp_session.call_tool.assert_awaited_once_with("fixtures", arguments={})
    agent.ollama.chat.assert_not_awaited()
    assert agent.messages == completed_history

    (record,) = [record for record in caplog.records if record.name == logger_name]
    assert (record.levelno, record.tool_name, record.outcome) == (
        logging.WARNING,
        "fixtures",
        "timeout",
    )
    assert record.duration_ms >= 0
    assert record.turn_id


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
