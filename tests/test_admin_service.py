import pytest
from pydantic import ValidationError

from football_team_assistant.services.admin_service import (
    AvailabilityBatch,
    DeleteConfirmation,
    FixtureFields,
    NewPlayer,
    PlayerFields,
)


@pytest.mark.parametrize("rating", [1, 3.5, 6])
def test_player_rating_accepts_whole_and_half_points(rating: float) -> None:
    player = NewPlayer.model_validate({"name": "  Player  ", "rating": rating})
    assert player.name == "Player"
    assert player.rating == rating
    assert player.can_play_goalkeeper is False


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "  "},
        {"name": "x" * 101},
        {"rating": 0.5},
        {"rating": 6.5},
        {"rating": 3.51},
        {"rating": "3.5"},
        {"can_play_goalkeeper": 1},
    ],
)
def test_invalid_player_fields_are_rejected(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        NewPlayer.model_validate({"name": "Player", "rating": 3.5, **fields})


def test_player_update_requires_goalkeeper_flag() -> None:
    with pytest.raises(ValidationError):
        PlayerFields.model_validate({"name": "Player", "rating": 3.5})


@pytest.mark.parametrize("home", [False, True])
def test_fixture_accepts_both_designations(home: bool) -> None:
    fixture = FixtureFields(date="2028-02-29", opponent="  FC  ", home=home)
    assert fixture.opponent == "FC"
    assert fixture.home is home


@pytest.mark.parametrize(
    "fields",
    [
        {"date": "2026-02-29"},
        {"date": "20261128"},
        {"opponent": " "},
        {"opponent": "x" * 151},
        {"home": 0},
    ],
)
def test_invalid_fixture_fields_are_rejected(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        FixtureFields.model_validate(
            {"date": "2026-11-28", "opponent": "FC", "home": False, **fields}
        )


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_delete_requires_explicit_boolean_confirmation(value: object) -> None:
    with pytest.raises(ValidationError):
        DeleteConfirmation.model_validate({"confirmed": value})


@pytest.mark.parametrize(
    "changes",
    [
        [],
        [{"player_id": 1, "available": True}, {"player_id": 1, "available": False}],
        [{"player_id": 1, "available": None}],
        [{"player_id": True, "available": False}],
        [{"player_id": 0, "available": True}],
    ],
)
def test_invalid_batches_are_rejected(changes: list[dict[str, object]]) -> None:
    with pytest.raises(ValidationError):
        AvailabilityBatch.model_validate({"changes": changes})
