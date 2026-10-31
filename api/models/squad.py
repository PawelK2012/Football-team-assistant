from pydantic import BaseModel

from api.models.fixture import Fixture
from api.models.player import Player


class SquadResult(BaseModel):
    fixture: Fixture

    squad_a: list[Player]
    squad_b: list[Player]

    average_rating_a: float
    average_rating_b: float
    balance_difference: float

    goalkeeper_a: Player
    goalkeeper_b: Player