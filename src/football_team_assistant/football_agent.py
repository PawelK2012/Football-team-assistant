import json
from datetime import datetime
from zoneinfo import ZoneInfo

from football_team_assistant.formatters import (
    format_available_players,
    format_squads,
    validate_squads,
)

from football_team_assistant.tool_validation import validate_tool_arguments

MODEL = "qwen3:8b"
MAX_TOOL_ITERATIONS = 10


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

For player availability:
- Use available_players with the correct fixture_id.

For squad generation:
- Use generate_match_squads with the correct fixture_id.
- Do not generate or modify squads yourself.
- Goalkeepers are already included in squad player lists.
- You do not need to call available_players before generating squads.

Python handles exact player lists and squad formatting.
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


class FootballAgent:
    def __init__(self, ollama, mcp_session, tools):
        self.ollama = ollama
        self.mcp_session = mcp_session
        self.tools = tools

        self.tool_names = {tool["function"]["name"] for tool in tools}

        self.messages = [
            {
                "role": "system",
                "content": build_system_prompt(),
            }
        ]

    async def ask(self, question: str) -> str:
        self.messages.append(
            {
                "role": "user",
                "content": question,
            }
        )

        # A direct data request must be answered from the
        # corresponding tool, not from a model-generated list.
        requested_tool = None

        lower_question = question.lower()

        if (
            any(
                word in lower_question
                for word in (
                    "generate",
                    "create",
                    "build",
                )
            )
            and "squad" in lower_question
        ):
            requested_tool = "generate_match_squads"

        elif "available" in lower_question or "availability" in lower_question:
            requested_tool = "available_players"

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self.ollama.chat(
                model=MODEL,
                messages=self.messages,
                tools=self.tools,
            )

            self.messages.append(response.message)
            tool_calls = response.message.tool_calls or []

            if not tool_calls:
                if requested_tool is not None:
                    raise RuntimeError(f"Agent did not call required tool: {requested_tool}")

                return response.message.content or ""

            final_output = None

            for call in tool_calls:
                name = call.function.name
                arguments = call.function.arguments or {}

                validate_tool_arguments(
                    name=name,
                    arguments=arguments,
                    tools=self.tools,
                )

                print(f"[MCP] Calling {name}: {arguments}")

                result = await self.mcp_session.call_tool(
                    name,
                    arguments=arguments,
                )

                data = extract_tool_result(result)

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(data, default=str),
                    }
                )

                if name == "generate_match_squads":
                    validate_squads(data)
                    formatted = format_squads(data)

                elif name == "available_players":
                    formatted = format_available_players(data)

                else:
                    formatted = None

                # Only finish when the requested tool has
                # actually produced the requested result.
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
