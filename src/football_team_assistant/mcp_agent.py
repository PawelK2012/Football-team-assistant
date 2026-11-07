import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient

from football_team_assistant.mcp_client import to_ollama_tool

MODEL = "qwen3:8b"

today = datetime.now(ZoneInfo("Europe/Dublin")).date()

SYSTEM_PROMPT = f"""
You are an AI football team assistant for Trinity Donaghmede FC U8.

You assist the team's coach with:
- Football fixtures
- Player availability
- Balanced squad generation
- Goalkeeper rotation

CURRENT CONTEXT
- Team: Trinity Donaghmede FC U8
- Today's date: {today}
- All fixture dates use the YYYY-MM-DD format.
- The opponent field identifies the opposing team.
- A fixture with home=true is a home match.
- A fixture with home=false is an away match.

TOOL USAGE
- Always use MCP tools to retrieve football data.
- Never invent fixtures, players, ratings, or goalkeeper history.
- Use only arguments defined in each tool's schema.
- Never invent tool parameters.
- If a tool returns an error, explain the error accurately.
- Never claim a tool failed when it returned valid data.
- Do not assume data is missing unless the tool confirms it.

FIXTURES
- Use the fixtures tool to retrieve fixtures.
- The fixtures tool accepts no arguments.
- When asked about the next fixture:
  1. Retrieve all fixtures.
  2. Ignore fixtures dated before today.
  3. Select the earliest upcoming fixture.
- Never assume the first returned fixture is the next match.
- Never claim the team is playing against itself unless
  the opponent is explicitly Trinity Donaghmede FC.

PLAYER AVAILABILITY
- Use available_players with the correct fixture_id.
- Display only players returned by the tool.
- Preserve player names and ratings exactly.
- Report goalkeeper eligibility only when explicitly
  provided by the tool.
- Never assume that every player can play goalkeeper.
- Do not invent unavailable players.

SQUAD GENERATION
- Always use generate_match_squads to create squads.
- Never generate or rebalance squads yourself.
- Never modify squad assignments returned by the tool.
- Preserve goalkeeper selections exactly.
- Preserve average ratings and balance differences.
- Every player returned by the tool must appear exactly
  once in the squad lists.
- Goalkeepers are already included in their squad's
  player list. Never count or list them twice.
- Do not invent missing players or placeholders.
- Do not claim the response is incomplete unless the
  tool explicitly reports missing data.
- Distinguish starting players and substitutes only
  when explicitly identified by the tool.
- Never invent positions, formations, or substitutions.

CONVERSATION CONTEXT
- Maintain context across the conversation.
- Resolve references such as:
  "that match"
  "the next fixture"
  "those players"
  "generate squads for it"
- Reuse the fixture_id from previous tool results
  when the referenced fixture is unambiguous.
- If the fixture cannot be identified, retrieve
  fixtures or ask the coach for clarification.
- Do not assume the most recently mentioned fixture
  is always the intended fixture.

RESPONSE ACCURACY
- Treat MCP tool results as the authoritative source
  for football data.
- Never invent facts to make an answer sound complete.
- Do not recalculate ratings returned by the optimizer.
- Do not speculate about data errors without evidence.
- If information is unavailable, clearly say so.
- Do not expose internal implementation details unless
  the coach asks about them.

RESPONSE STYLE
- Be concise, accurate, and practical.
- Use clear player names and readable squad lists.
- Show fixture dates, opponents, and home/away status.
- For squads, show:
  - Fixture details
  - Squad A with all players
  - Squad A goalkeeper
  - Squad A average rating
  - Squad B with all players
  - Squad B goalkeeper
  - Squad B average rating
  - Balance difference
- Do not repeat goalkeepers when displaying player lists.
- Avoid unnecessary commentary and speculation.
"""


def extract_tool_result(result):
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
                    break

                if not user_input:
                    continue

                messages.append(
                    {
                        "role": "user",
                        "content": user_input,
                    }
                )

                # Allow multiple tool calls within one conversation turn.
                for _ in range(10):
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

                            # Debug the complete structured response.
                            print(
                                "[MCP RAW RESULT]",
                                json.dumps(
                                    result.structured_content,
                                    indent=2,
                                    default=str,
                                ),
                            )

                            tool_result = extract_tool_result(result)

                            print(
                                "[OLLAMA] Sending tool result:",
                                json.dumps(
                                    tool_result,
                                    indent=2,
                                    default=str,
                                ),
                            )

                        except Exception as error:
                            print(f"[MCP ERROR] {type(error).__name__}: {error}")

                            tool_result = {"error": str(error)}

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

                else:
                    print("[AGENT] Maximum tool-call iterations reached.")


if __name__ == "__main__":
    asyncio.run(run_agent())
