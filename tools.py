from data import (
    AVAILABILITY,
    FIXTURES,
    GOALKEEPER_HISTORY,
    PLAYERS,
)
from squad_optimizer import create_balanced_squads
from state import state


def get_fixtures() -> list:
    """Get upcoming football fixtures."""

    return FIXTURES


def get_available_players(fixture_id: int) -> list:
    """
    Get players available for a specific fixture.

    Args:
        fixture_id: The ID of the fixture.
    """

    state["current_fixture_id"] = fixture_id

    available_player_ids = {
        entry["player_id"]
        for entry in AVAILABILITY
        if (
            entry["fixture_id"] == fixture_id
            and entry["available"]
        )
    }

    return [
        player
        for player in PLAYERS
        if player["id"] in available_player_ids
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
                    "date": entry["date"],
                    "player_id": player["id"],
                    "player": player["name"],
                }
            )

    return history

def create_current_match_squads() -> dict:
    """
    Create balanced squads for the fixture currently being worked on.
    """

    fixture_id = state["current_fixture_id"]

    if fixture_id is None:
        raise ValueError(
            "No current fixture has been selected."
        )

    return create_match_squads(fixture_id)


def create_match_squads(fixture_id: int) -> dict:

    fixture = next(
        (
            fixture
            for fixture in FIXTURES
            if fixture["id"] == fixture_id
        ),
        None,
    )

    if fixture is None:
        raise ValueError(
            f"Fixture {fixture_id} does not exist."
        )

    state["current_fixture_id"] = fixture_id

    available_players = get_available_players(
        fixture_id
    )

    squads = create_balanced_squads(
        available_players,
        GOALKEEPER_HISTORY,
    )

    return {
        "fixture": fixture,
        **squads,
    }

TOOLS = {
    "get_fixtures": get_fixtures,
    "get_available_players": get_available_players,
    "get_goalkeeper_history": get_goalkeeper_history,
    "create_match_squads": create_match_squads,
    "create_current_match_squads": create_current_match_squads,
}


TOOL_DEFINITIONS = [
    get_fixtures,
    get_available_players,
    get_goalkeeper_history,
    create_match_squads,
    create_current_match_squads,
]