from pydantic import BaseModel


class Fixture(BaseModel):
    id: int
    date: str
    opponent: str
    home: bool
