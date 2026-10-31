from fastapi import APIRouter

from api.models.fixture import Fixture
from api.models.player import Player
from repositories.fixture_repository import (
    get_fixtures,
)
from repositories.player_repository import (
    get_available_players,
)

router = APIRouter(
    prefix="/fixtures",
    tags=["fixtures"],
)


@router.get(
    "",
    response_model=list[Fixture],
)
def list_fixtures():
    return get_fixtures()


@router.get(
    "/{fixture_id}/available-players",
    response_model=list[Player],
)
def list_available_players(
    fixture_id: int,
):
    return get_available_players(fixture_id)
