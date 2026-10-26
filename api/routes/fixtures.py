from fastapi import APIRouter

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


@router.get("")
def list_fixtures():
    return get_fixtures()


@router.get("/{fixture_id}/available-players")
def list_available_players(
    fixture_id: int,
):
    return get_available_players(
        fixture_id
    )