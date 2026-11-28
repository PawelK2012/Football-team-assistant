from datetime import date
from typing import Annotated, Literal, Self

from psycopg.rows import DictRow
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from football_team_assistant.repositories import (
    availability_repository,
    fixture_repository,
    player_repository,
)
from football_team_assistant.repositories.admin_records import delete_record


def valid_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Enter text without null characters.")
    return value


PlayerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(valid_text),
]
OpponentName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
    AfterValidator(valid_text),
]
RecordID = Annotated[int, Field(gt=0, le=2_147_483_647)]


class AdminInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class PlayerFields(AdminInput):
    name: PlayerName
    rating: Annotated[float, Field(ge=1, le=6)]
    can_play_goalkeeper: bool

    @field_validator("rating")
    @classmethod
    def half_point_rating(cls, rating: float) -> float:
        if not (rating * 2).is_integer():
            raise ValueError("Use a half-point rating from 1.0 to 6.0.")
        return rating


class NewPlayer(PlayerFields):
    can_play_goalkeeper: bool = False


class FixtureFields(AdminInput):
    date: Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
    opponent: OpponentName
    home: bool

    @field_validator("date")
    @classmethod
    def calendar_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class DeleteConfirmation(AdminInput):
    confirmed: Literal[True]

    @field_validator("confirmed", mode="before")
    @classmethod
    def explicit_confirmation(cls, value: object) -> object:
        if value is not True:
            raise ValueError("Confirm this deletion first.")
        return value


class AvailabilityChange(AdminInput):
    player_id: RecordID
    available: bool


class AvailabilityBatch(AdminInput):
    changes: Annotated[list[AvailabilityChange], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_players(self) -> Self:
        if len({change.player_id for change in self.changes}) != len(self.changes):
            raise ValueError("Include each player only once.")
        return self


def list_players() -> list[DictRow]:
    return player_repository.list_admin_players()


def list_fixtures() -> list[DictRow]:
    return fixture_repository.list_admin_fixtures()


def get_availability(fixture_id: int) -> list[DictRow]:
    return availability_repository.get_roster(fixture_id)


def save_availability(fixture_id: int, batch: AvailabilityBatch) -> list[dict[str, int | bool]]:
    changes = {change.player_id: change.available for change in batch.changes}
    availability_repository.save_batch(fixture_id, changes)
    return [{"player_id": player_id, "available": value} for player_id, value in changes.items()]


def create_player(record: NewPlayer) -> DictRow:
    return player_repository.create_admin_player(
        record.name, record.rating, record.can_play_goalkeeper
    )


def update_player(player_id: int, record: PlayerFields) -> DictRow:
    return player_repository.update_admin_player(
        player_id, record.name, record.rating, record.can_play_goalkeeper
    )


def delete_player(player_id: int) -> None:
    delete_record("players", player_id)


def create_fixture(record: FixtureFields) -> DictRow:
    return fixture_repository.create_admin_fixture(record.date, record.opponent, record.home)


def update_fixture(fixture_id: int, record: FixtureFields) -> DictRow:
    return fixture_repository.update_admin_fixture(
        fixture_id, record.date, record.opponent, record.home
    )


def delete_fixture(fixture_id: int) -> None:
    delete_record("fixtures", fixture_id)
