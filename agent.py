import json

from ollama import chat

from tools import (
    TOOL_DEFINITIONS,
    TOOLS,
)

MODEL = "qwen3:8b"


SYSTEM_PROMPT = """
You are a football team assistant helping a youth football coach.

Use the provided tools whenever team data is required.

Never invent player availability, ratings, goalkeeper history,
fixture IDs, squad selections, player positions, or player roles.

You are responsible for resolving fixture IDs yourself.

If the coach refers to a fixture by opponent, date, or phrases such
as "next match", use get_fixtures to find the correct fixture.

Do not ask the coach for a fixture ID if it can be determined using
get_fixtures.

When asked who is available, list every available player returned
by the tool. Do not omit players or prioritize them based on rating
unless the coach asks you to.

Only describe a player as a goalkeeper if the provided data says
they can play goalkeeper.

If the coach asks to create squads for a named fixture, first resolve
the fixture using get_fixtures, then call create_match_squads with
the correct fixture ID.

If the coach asks to create squads for "this game", "that game",
"the current game", or does not specify a fixture, use
create_current_match_squads if a fixture has already been selected.

Use create_match_squads when the coach explicitly identifies a
fixture by opponent, date, or fixture ID.
"""


messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT,
    }
]


def run_agent(user_input: str) -> str:

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    while True:
        response = chat(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        messages.append(response.message)

        if not response.message.tool_calls:
            return response.message.content

        for call in response.message.tool_calls:
            tool_name = call.function.name
            arguments = call.function.arguments

            print(f"\n[Agent] Calling: {tool_name}")
            print(f"[Agent] Arguments: {arguments}")

            tool = TOOLS.get(tool_name)

            if tool is None:
                result = {"error": f"Unknown tool: {tool_name}"}

            else:
                try:
                    result = tool(**arguments)

                except Exception as error:
                    result = {"error": str(error)}

            print(f"[Tool] Result: {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(result),
                }
            )
