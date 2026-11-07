
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
You are a football team assistant for an U8 football coach.

Today's date is {today}.

Use the available MCP tools to answer questions about fixtures,
player availability, and match squads.

Rules:
- Never invent fixtures, players, ratings, or goalkeeper eligibility.
- Always use MCP tools to retrieve football data.
- Never generate squads yourself. Use the squad generation tool.
- Never modify squad assignments returned by the tool.
- Preserve goalkeeper selections exactly.
- Preserve calculated average ratings.
- If information is missing, say it is unavailable.

When asked about the next fixture:
- Retrieve fixtures using the fixtures tool.
- Ignore fixtures before today's date.
- Select the earliest upcoming fixture.

When presenting available players:
- Display only players returned by the availability tool.
- Report goalkeeper eligibility only if explicitly provided.
- Do not assume all available players can play goalkeeper.

When presenting generated squads:
- The goalkeeper is already a member of the squad.
- Never count the goalkeeper twice.
- Never invent missing players or placeholders.
- Never claim the response is incomplete unless the tool
  explicitly reports an error or missing data.
- Display every player returned by the squad generation tool.
- Preserve squad assignments and goalkeeper selections.
- Do not recalculate average ratings.
- Distinguish starters and substitutes only if the tool
  explicitly identifies them.
"""


def extract_tool_result(result):
    """
    Extract structured data from an MCP tool response.
    """
    if result.is_error:
        error_message = " ".join(
            item.text
            for item in result.content
            if item.type == "text"
        )
        raise RuntimeError(error_message or "MCP tool failed")

    if result.structured_content is not None:
        data = result.structured_content

        # Unwrap the standard result wrapper when present.
        if isinstance(data, dict) and set(data) == {"result"}:
            return data["result"]

        return data

    return [
        item.text
        for item in result.content
        if item.type == "text"
    ]


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

            ollama_tools = [
                to_ollama_tool(tool)
                for tool in discovered_tools.tools
            ]

            tool_names = {
                tool.name for tool in discovered_tools.tools
            }

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
                        print(
                            f"[OLLAMA ERROR] "
                            f"{type(error).__name__}: {error}"
                        )
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
                                raise ValueError(
                                    f"Unknown MCP tool: {name}"
                                )

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
                            print(
                                f"[MCP ERROR] "
                                f"{type(error).__name__}: {error}"
                            )

                            tool_result = {
                                "error": str(error)
                            }

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
                    print(
                        "[AGENT] Maximum tool-call iterations reached."
                    )


if __name__ == "__main__":
    asyncio.run(run_agent())
