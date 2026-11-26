import asyncio
import json
import logging
from datetime import datetime
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

from mcp import ClientSession
from mcp.types import CallToolResult
from ollama import AsyncClient

from football_team_assistant.fixture_resolution import (
    resolve_fixture,
)
from football_team_assistant.formatters import (
    format_available_players,
    format_squads,
    validate_squads,
)
from football_team_assistant.tool_validation import (
    validate_tool_arguments,
)

logger = logging.getLogger(__name__)

MODEL = "qwen3:8b"
MAX_TOOL_ITERATIONS = 10
DEFAULT_TOOL_TIMEOUT_SECONDS = 10.0

FIXTURE_TOOLS = {
    "available_players",
    "generate_match_squads",
}


def build_system_prompt() -> str:
    today = datetime.now(ZoneInfo("Europe/Dublin")).date()

    return f"""
You are an AI football team assistant for Trinity Donaghmede FC U8.

Today's date is {today}.

Use MCP tools for all football data.
Never invent players, fixtures, ratings, or goalkeeper history.
Use only arguments defined by the tool schemas.

The fixtures tool accepts no arguments.
The opponent field identifies the opposing team.

For the next fixture:
- Retrieve fixtures.
- Select the earliest fixture on or after today.
- Do not describe past fixtures as upcoming.

For player availability:
- Use available_players with the correct fixture_id.

For squad generation:
- Use generate_match_squads with the correct fixture_id.
- Do not generate or modify squads yourself.
- Goalkeepers are already included in squad player lists.
- You do not need to call available_players before generating squads.

For follow-up questions:
- Reuse the currently selected fixture unless the coach specifies another.
- Never invent a fixture ID.
- When the coach selects a different opponent, retrieve fixtures to resolve its ID.

Python handles fixture selection, exact player lists,
and squad formatting.

Never reconstruct player lists from memory.
Maintain conversation context across questions.
"""


def extract_tool_result(result):
    if result.is_error:
        message = " ".join(item.text for item in result.content if item.type == "text")
        raise RuntimeError(message or "MCP tool failed")

    if result.structured_content is not None:
        data = result.structured_content
    else:
        items = [item.text for item in result.content if item.type == "text"]

        if len(items) == 1:
            try:
                data = json.loads(items[0])
            except json.JSONDecodeError:
                data = items[0]
        else:
            data = items

    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]

    return data


def validate_availability_result(name: str, data: object) -> None:
    if name != "available_players":
        return

    error_prefix = "available_players returned an invalid result"
    if not isinstance(data, list):
        raise ValueError(f"{error_prefix}: expected a list")

    for index, player in enumerate(data, start=1):
        if not isinstance(player, dict):
            raise ValueError(f"{error_prefix}: expected a player record at position {index}")

        for field in ("name", "rating"):
            if field not in player:
                raise ValueError(f"{error_prefix}: player {index} is missing {field}")


class _MCPToolTimeout(TimeoutError):
    """Identify tool timeouts so the agent can roll back the interrupted turn."""


class FootballAgent:
    def __init__(
        self,
        ollama: AsyncClient,
        mcp_session: ClientSession,
        tools: list[dict],
        *,
        tool_timeout_seconds: float = DEFAULT_TOOL_TIMEOUT_SECONDS,
    ) -> None:
        self.ollama = ollama
        self.mcp_session = mcp_session
        self.tools = tools
        self.tool_timeout_seconds = tool_timeout_seconds
        self._turn_lock = asyncio.Lock()

        self.tool_names = {tool["function"]["name"] for tool in tools}

        self.current_fixture_id: int | None = None

        self.messages = [
            {
                "role": "system",
                "content": build_system_prompt(),
            }
        ]

    async def _call_tool(
        self, name: str, arguments: dict, *, turn_id: str | None = None
    ) -> CallToolResult:
        started_at = perf_counter()
        try:
            async with asyncio.timeout(self.tool_timeout_seconds):
                result = await self.mcp_session.call_tool(name, arguments=arguments)
        except TimeoutError as error:
            logger.warning(
                "MCP tool call timed out",
                extra={
                    "turn_id": turn_id,
                    "tool_name": name,
                    "outcome": "timeout",
                    "duration_ms": (perf_counter() - started_at) * 1_000,
                },
            )
            raise _MCPToolTimeout(f"MCP tool '{name}' timed out") from error

        logger.info(
            "MCP tool response received",
            extra={
                "turn_id": turn_id,
                "tool_name": name,
                "outcome": "response_received",
                "duration_ms": (perf_counter() - started_at) * 1_000,
            },
        )
        return result

    async def select_fixture(
        self,
        question: str,
        *,
        turn_id: str | None = None,
    ) -> int | None:
        """
        Resolve and validate a fixture using MCP data.

        Supports:
        - Explicit fixture IDs
        - Opponent names
        - Follow-up questions using current fixture
        """
        result = await self._call_tool("fixtures", {}, turn_id=turn_id)

        fixtures = extract_tool_result(result)

        selected_id = resolve_fixture(
            question=question,
            fixtures=fixtures,
            current_fixture_id=self.current_fixture_id,
        )

        if selected_id is not None:
            self.current_fixture_id = selected_id

            print(f"[FIXTURE] Selected fixture {selected_id}")

        return selected_id

    async def execute_fixture_tool(
        self,
        name: str,
        fixture_id: int,
        *,
        turn_id: str | None = None,
    ) -> str:
        """
        Execute a fixture-specific MCP tool.

        Python controls the fixture ID and formats
        the response deterministically.
        """
        arguments = {
            "fixture_id": fixture_id,
        }

        validate_tool_arguments(
            name=name,
            arguments=arguments,
            tools=self.tools,
        )

        print(f"[MCP] Calling {name}: {arguments}")

        result = await self._call_tool(name, arguments, turn_id=turn_id)

        data = extract_tool_result(result)
        validate_availability_result(name, data)

        self.current_fixture_id = fixture_id

        self.messages.append(
            {
                "role": "tool",
                "tool_name": name,
                "content": json.dumps(data, default=str),
            }
        )

        if name == "available_players":
            formatted = format_available_players(data)

        elif name == "generate_match_squads":
            validate_squads(data)
            formatted = format_squads(data)

        else:
            raise ValueError(f"Unsupported fixture tool: {name}")

        self.messages.append(
            {
                "role": "assistant",
                "content": formatted,
            }
        )

        return formatted

    async def ask(self, question: str) -> str:
        async with self._turn_lock:
            turn_id = uuid4().hex
            turn_start = len(self.messages)
            previous_fixture_id = self.current_fixture_id
            try:
                return await self._run_turn(question, turn_id=turn_id)
            except _MCPToolTimeout as error:
                del self.messages[turn_start:]
                self.current_fixture_id = previous_fixture_id
                raise TimeoutError(str(error)) from error.__cause__

    async def _run_turn(self, question: str, *, turn_id: str) -> str:
        self.messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        requested_tool = None
        lower_question = question.lower()

        if (
            any(
                word in lower_question
                for word in (
                    "generate",
                    "create",
                    "build",
                    "make",
                )
            )
            and "squad" in lower_question
        ):
            requested_tool = "generate_match_squads"

        elif "available" in lower_question or "availability" in lower_question:
            requested_tool = "available_players"

        # Resolve the fixture before invoking Ollama.
        if requested_tool is not None:
            selected_id = await self.select_fixture(question, turn_id=turn_id)

            if selected_id is None:
                return "Which fixture do you mean? Please specify a fixture ID or opponent."

        for _ in range(MAX_TOOL_ITERATIONS):
            messages = list(self.messages)

            if self.current_fixture_id is not None:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Current selected fixture ID: "
                            f"{self.current_fixture_id}. "
                            "Use this fixture for follow-up questions "
                            "unless the coach explicitly selects "
                            "another fixture."
                        ),
                    }
                )

            response = await self.ollama.chat(
                model=MODEL,
                messages=messages,
                tools=self.tools,
            )

            self.messages.append(response.message)

            tool_calls = response.message.tool_calls or []
            logger.info(
                "Ollama model decision received",
                extra={"turn_id": turn_id, "tool_call_count": len(tool_calls)},
            )

            # Qwen sometimes answers without calling
            # the required MCP tool.
            if not tool_calls:
                if requested_tool is not None:
                    return await self.execute_fixture_tool(
                        name=requested_tool,
                        fixture_id=self.current_fixture_id,
                        turn_id=turn_id,
                    )

                return response.message.content or ""

            final_output = None

            for call in tool_calls:
                name = call.function.name
                arguments = call.function.arguments or {}

                # Enforce fixture context in Python.
                if name in FIXTURE_TOOLS:
                    if self.current_fixture_id is None:
                        raise ValueError("No fixture selected.")

                    arguments = {
                        **arguments,
                        "fixture_id": self.current_fixture_id,
                    }

                validate_tool_arguments(
                    name=name,
                    arguments=arguments,
                    tools=self.tools,
                )

                print(f"[MCP] Calling {name}: {arguments}")

                result = await self._call_tool(name, arguments, turn_id=turn_id)

                data = extract_tool_result(result)
                validate_availability_result(name, data)

                if name in FIXTURE_TOOLS:
                    self.current_fixture_id = arguments["fixture_id"]

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(
                            data,
                            default=str,
                        ),
                    }
                )

                if name == "generate_match_squads":
                    validate_squads(data)
                    formatted = format_squads(data)

                elif name == "available_players":
                    formatted = format_available_players(data)

                else:
                    formatted = None

                if formatted is not None and (requested_tool is None or requested_tool == name):
                    final_output = formatted

            if final_output is not None:
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": final_output,
                    }
                )

                return final_output

        raise RuntimeError(f"Agent exceeded {MAX_TOOL_ITERATIONS} iterations")
