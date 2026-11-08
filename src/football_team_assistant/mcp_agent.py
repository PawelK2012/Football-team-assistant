import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient

from football_team_assistant.formatters import (
    format_available_players,
    format_squads,
    validate_squads,
)
from football_team_assistant.mcp_client import to_ollama_tool

MODEL = "qwen3:8b"
MAX_TOOL_ITERATIONS = 10

today = datetime.now(ZoneInfo("Europe/Dublin")).date()

SYSTEM_PROMPT = f"""
You are an AI football team assistant for Trinity Donaghmede FC U8.

Today's date is {today}.
All fixture dates use YYYY-MM-DD format.

Your responsibilities:
- Answer questions about fixtures.
- Retrieve player availability.
- Generate balanced match squads.
- Help the coach understand football data.

TOOL USAGE
- Always use MCP tools for football data.
- Never invent fixtures, players, ratings, or goalkeeper history.
- Use only arguments defined in each tool's schema.
- The fixtures tool accepts no arguments.
- Never generate squads yourself.
- Always use generate_match_squads for squad generation.
- Never modify tool results.
- If a tool fails, report the error accurately.

FIXTURES
- The opponent field identifies the opposing team.
- home=true means a home match.
- home=false means an away match.
- To find the next fixture, retrieve fixtures and select
  the earliest fixture on or after today's date.
- Never claim the team plays itself unless the opponent
  is explicitly Trinity Donaghmede FC.

PLAYER AVAILABILITY
- Use available_players with the correct fixture_id.
- Do not invent or omit players.
- Report goalkeeper eligibility only if supplied.

SQUAD GENERATION
- Use generate_match_squads with the correct fixture_id.
- Never rebalance squads yourself.
- Preserve all player assignments and goalkeeper selections.
- Goalkeepers are already included in their squad lists.
- Never count a goalkeeper twice.
- Do not invent substitutions or positions.

CONVERSATION
- Maintain context across questions.
- Resolve references such as "that match" or "those squads".
- Retrieve fixtures if the intended fixture is unclear.
- Ask for clarification if multiple fixtures match.

RESPONSE STYLE
- Be concise and accurate.
- Never speculate about data errors without evidence.
- Python handles exact player lists and squad formatting.
- Do not reconstruct player lists from memory.

When the coach requests squads, call generate_match_squads.
You do not need to call available_players first because
generate_match_squads retrieves the required player data.
"""


def extract_tool_result(result):
    """Normalize structured and text-based MCP responses."""

    if result.is_error:
        error_message = " ".join(item.text for item in result.content if item.type == "text")
        raise RuntimeError(error_message or "MCP tool failed")

    if result.structured_content is not None:
        data = result.structured_content
    else:
        text_items = [item.text for item in result.content if item.type == "text"]

        if len(text_items) == 1:
            try:
                data = json.loads(text_items[0])
            except json.JSONDecodeError:
                data = text_items[0]
        else:
            data = text_items

    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]

    return data


async def run_agent():
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "python",
            "-m",
            "football_team_assistant.mcp_server.server",
        ],
    )

    ollama = AsyncClient()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            discovered_tools = await session.list_tools()

            ollama_tools = [to_ollama_tool(tool) for tool in discovered_tools.tools]

            tool_names = {tool.name for tool in discovered_tools.tools}

            print(
                "Connected to MCP server. Tools:",
                sorted(tool_names),
            )

            while True:
                try:
                    user_input = input("\nCoach: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print("\nGoodbye!")
                    break

                if user_input.lower() in {"quit", "exit"}:
                    print("Goodbye!")
                    break

                if not user_input:
                    continue

                messages.append(
                    {
                        "role": "user",
                        "content": user_input,
                    }
                )

                # Process the user's request.
                # MAX_TOOL_ITERATIONS is a safety limit to prevent agent from getting stuck
                # in an infinite tool-calling loop.
                for _ in range(MAX_TOOL_ITERATIONS):
                    try:
                        response = await ollama.chat(
                            model=MODEL,
                            messages=messages,
                            tools=ollama_tools,
                        )
                    except Exception as error:
                        print(f"[OLLAMA ERROR] {type(error).__name__}: {error}")
                        break

                    messages.append(response.message)

                    tool_calls = response.message.tool_calls or []

                    if not tool_calls:
                        print(
                            "\nAssistant:",
                            response.message.content,
                        )
                        break

                    formatted_output = None
                    tool_failed = False

                    # Execute all requested MCP tool calls.
                    for tool_call in tool_calls:
                        name = tool_call.function.name
                        arguments = tool_call.function.arguments or {}

                        print(f"[MCP] Calling {name}: {arguments}")

                        try:
                            if name not in tool_names:
                                raise ValueError(f"Unknown MCP tool: {name}")

                            result = await session.call_tool(
                                name,
                                arguments=arguments,
                            )

                            tool_result = extract_tool_result(result)

                            # Keep debug logging for development.
                            print(
                                "[MCP RESULT]",
                                json.dumps(
                                    tool_result,
                                    indent=2,
                                    default=str,
                                ),
                            )

                            # Format structured data in Python.
                            # Do not ask the LLM to recreate these lists.
                            if name == "generate_match_squads":
                                validate_squads(tool_result)
                                formatted_output = format_squads(tool_result)

                            elif name == "available_players":
                                formatted_output = format_available_players(tool_result)

                        except Exception as error:
                            print(f"[MCP ERROR] {type(error).__name__}: {error}")

                            tool_result = {"error": str(error)}
                            tool_failed = True
                            formatted_output = None

                        # Always record the tool response so the LLM
                        # can maintain conversation context.
                        messages.append(
                            {
                                "role": "tool",
                                "tool_name": name,
                                "content": json.dumps(
                                    tool_result,
                                    default=str,
                                ),
                            }
                        )

                    # If a structured result is available, display
                    # the verified Python output directly.
                    if formatted_output is not None and not tool_failed:
                        print("\nAssistant:\n")
                        print(formatted_output)

                        # Record the actual answer in conversation
                        # history for follow-up questions.
                        messages.append(
                            {
                                "role": "assistant",
                                "content": formatted_output,
                            }
                        )
                        break

                    # Otherwise continue the LLM loop.
                    # This allows chained calls, for example:
                    # fixtures -> available_players.

                else:
                    raise RuntimeError(f"Agent exceeded {MAX_TOOL_ITERATIONS} tool iterations")


if __name__ == "__main__":
    asyncio.run(run_agent())
