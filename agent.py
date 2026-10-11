import json

from ollama import chat

import data.goalkeeper_history as goalkeeper_history_data

# -------------------------------------------------------------------
# Data
# -------------------------------------------------------------------
import data.players as players_data
from squad_optimizer import create_balanced_squads

MODEL = "qwen3:8b"


# -------------------------------------------------------------------
# Tools
# -------------------------------------------------------------------
def create_match_squads() -> dict:
    """
    Create two balanced squads for the upcoming match.

    Uses all available players, balances player ratings,
    ensures both squads contain an eligible goalkeeper,
    and rotates goalkeeper duty based on previous matches.
    """

    available_players = get_available_players()

    return create_balanced_squads(
        available_players,
        goalkeeper_history_data.GOALKEEPER_HISTORY,
    )


def get_available_players() -> list:
    """Get all players available for the upcoming football match."""

    return [player for player in players_data.PLAYERS if player["available"]]


def get_goalkeeper_history() -> list:
    """Get goalkeeper selections from previous matches, newest first."""

    history = []

    for entry in sorted(
        goalkeeper_history_data.GOALKEEPER_HISTORY,
        key=lambda item: item["date"],
        reverse=True,
    ):
        player = next(
            player
            for player in players_data.PLAYERS
            if player["id"] == entry["player_id"]
        )

        history.append(
            {
                "date": entry["date"],
                "player_id": player["id"],
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
    "create_match_squads": create_match_squads,
}


TOOL_DEFINITIONS = [
    get_available_players,
    get_goalkeeper_history,
    create_match_squads,
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
                "Never invent player availability, ratings, goalkeeper history, "
                "or squad selections. "
                "When the coach asks you to create or select squads, use the "
                "create_match_squads tool."
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
