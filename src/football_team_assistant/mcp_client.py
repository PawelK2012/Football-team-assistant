import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "python",
            "-m",
            "football_team_assistant.mcp_server.server",
        ],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            ollama_tools = [
                to_ollama_tool(tool)
                for tool in tools.tools
            ]

            for tool in ollama_tools:
                print(tool)
            
            # for tool in tools.tools:
            #     print(f"Tool: {tool.name}")
            #     print(f"Description: {tool.description}")
            #     print(f"Schema: {tool.input_schema}")
            #     print()

            result = await session.call_tool(
                "fixtures",
                arguments={},
            )

            print("Fixtures:", result)

            result = await session.call_tool(
                "generate_match_squads",
                arguments={"fixture_id": 6},
            )

            print(json.dumps(result.structured_content, indent=2))

def to_ollama_tool(tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


if __name__ == "__main__":
    asyncio.run(main())
