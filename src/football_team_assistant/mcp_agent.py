import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient

from football_team_assistant.football_agent import FootballAgent
from football_team_assistant.mcp_client import to_ollama_tool


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

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            discovered = await session.list_tools()
            tools = [to_ollama_tool(tool) for tool in discovered.tools]

            agent = FootballAgent(
                ollama=AsyncClient(),
                mcp_session=session,
                tools=tools,
            )

            print(
                "Connected to MCP server. Tools:",
                sorted(agent.tool_names),
            )

            while True:
                try:
                    question = input("\nCoach: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    break

                if question.lower() in {"exit", "quit"}:
                    break

                if not question:
                    continue

                try:
                    answer = await agent.ask(question)
                    print(f"\nAssistant:\n{answer}")

                except Exception as error:
                    print(f"\n[AGENT ERROR] {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(run_agent())
