from football_team_assistant.repositories.fixture_repository import (
    get_fixture,
)
from football_team_assistant.repositories.goalkeeper_repository import (
    get_goalkeeper_history,
)
from football_team_assistant.repositories.player_repository import (
    get_available_players,
)
from football_team_assistant.squad_optimizer import create_balanced_squads


def create_match_squads(
    fixture_id: int,
) -> dict:

    fixture = get_fixture(fixture_id)

    if fixture is None:
        raise ValueError(f"Fixture {fixture_id} does not exist.")

    available_players = get_available_players(fixture_id)

    goalkeeper_history = get_goalkeeper_history()

    squads = create_balanced_squads(
        available_players,
        goalkeeper_history,
    )

    return {
        "fixture": fixture,
        **squads,
    }
