import json

from ollama import chat


MODEL = "qwen3:8b"


# -------------------------------------------------------------------
# Data
# -------------------------------------------------------------------

PLAYERS = [
    {"id": 1, "name": "Henry", "available": True},
    {"id": 2, "name": "Jack", "available": True},
    {"id": 3, "name": "Ben", "available": False},
    {"id": 4, "name": "Milo", "available": True},
    {"id": 5, "name": "Calum", "available": True},
]


GOALKEEPER_HISTORY = [
    {"match": "Match 1", "player_id": 1},
    {"match": "Match 1", "player_id": 4},
    {"match": "Match 2", "player_id": 2},
    {"match": "Match 2", "player_id": 5},
]


# -------------------------------------------------------------------
# Tools
# -------------------------------------------------------------------

def get_available_players() -> list:
    """Get all players available for the upcoming football match."""

    return [
        player
        for player in PLAYERS
        if player["available"]
    ]


def get_goalkeeper_history() -> list:
    """Get goalkeeper selections from previous matches."""

    history = []

    for entry in GOALKEEPER_HISTORY:
        player = next(
            (
                player
                for player in PLAYERS
                if player["id"] == entry["player_id"]
            ),
            None,
        )

        if player:
            history.append(
                {
                    "match": entry["match"],
                    "player": player["name"],
                }
            )

    return history


# -------------------------------------------------------------------
# Tool registry
# -------------------------------------------------------------------

TOOLS = {
    "get_available_players": get_available_players,
    "get_goalkeeper_history": get_goalkeeper_history,
}


TOOL_DEFINITIONS = [
    get_available_players,
    get_goalkeeper_history,
]


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------

def run_agent(user_input: str) -> str:

    messages = [
        {
            "role": "system",
            "content": (
                "You are a football team assistant helping a youth football coach. "
                "Use the provided tools whenever team data is required. "
                "Never invent player availability or goalkeeper history."
            ),
        },
        {
            "role": "user",
            "content": user_input,
        },
    ]

    while True:

        response = chat(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        messages.append(response.message)

        # No tool requested -> we have our final answer.
        if not response.message.tool_calls:
            return response.message.content

        # Execute every tool requested by the model.
        for call in response.message.tool_calls:

            tool_name = call.function.name
            arguments = call.function.arguments

            print(f"\n[Agent] Calling: {tool_name}")
            print(f"[Agent] Arguments: {arguments}")

            tool = TOOLS.get(tool_name)

            if tool is None:
                result = {
                    "error": f"Unknown tool: {tool_name}"
                }

            else:
                try:
                    result = tool(**arguments)
                except Exception as error:
                    result = {
                        "error": str(error)
                    }

            print(f"[Tool] Result: {result}")

            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(result),
                }
            )


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

if __name__ == "__main__":

    while True:

        user_input = input("\nCoach: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        answer = run_agent(user_input)

        print(f"\nAssistant: {answer}")