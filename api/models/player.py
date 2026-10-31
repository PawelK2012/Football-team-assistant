from pydantic import BaseModel


class Player(BaseModel):
    id: int
    name: str
    rating: float
    can_play_goalkeeper: bool