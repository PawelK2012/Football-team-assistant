from repositories.fixture_repository import (
    get_fixture as get_fixture_from_db,
)
from repositories.fixture_repository import (
    get_fixtures as get_fixtures_from_db,
)
from repositories.goalkeeper_repository import (
    get_goalkeeper_history as get_goalkeeper_history_from_db,
)
from repositories.player_repository import (
    get_available_players as get_available_players_from_db,
)
from services.match_service import (
    create_match_squads as create_match_squads_service,
)
from squad_optimizer import create_balanced_squads
from state import state


def get_fixtures() -> list:
    """Get upcoming football fixtures."""

    return get_fixtures_from_db()


def get_available_players(fixture_id: int) -> list:
    """
    Get players available for a specific fixture.

    Args:
        fixture_id: The ID of the fixture.
    """

    state["current_fixture_id"] = fixture_id

    return get_available_players_from_db(fixture_id)


def get_goalkeeper_history() -> list:
    """Get goalkeeper selections from previous matches."""

    return get_goalkeeper_history_from_db()


def create_current_match_squads() -> dict:
    """
    Create balanced squads for the fixture currently being worked on.
    """

    fixture_id = state["current_fixture_id"]

    if fixture_id is None:
        raise ValueError("No current fixture has been selected.")

    return create_match_squads(fixture_id)

def create_match_squads(
    fixture_id: int,
) -> dict:
    """
    Create two balanced squads for a specific fixture.

    Args:
        fixture_id: The ID of the fixture.
    """

    state["current_fixture_id"] = fixture_id

    return create_match_squads_service(
        fixture_id
    )


# def create_match_squads(fixture_id: int) -> dict:
#     """
#     Create two balanced squads for a specific fixture.

#     Args:
#         fixture_id: The ID of the fixture to create squads for.
#     """

#     fixture = get_fixture_from_db(fixture_id)

#     if fixture is None:
#         raise ValueError(f"Fixture {fixture_id} does not exist.")

#     state["current_fixture_id"] = fixture_id

#     available_players = get_available_players_from_db(fixture_id)

#     goalkeeper_history = get_goalkeeper_history_from_db()

#     squads = create_balanced_squads(
#         available_players,
#         goalkeeper_history,
#     )

#     return {
#         "fixture": fixture,
#         **squads,
#     }


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
