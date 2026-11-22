import pytest

from football_team_assistant.fixture_resolution import (
    extract_explicit_fixture_id,
    resolve_fixture,
)


@pytest.fixture
def fixtures():
    return [
        {
            "id": 5,
            "opponent": "Dunboyne FC",
            "date": "2026-11-01",
        },
        {
            "id": 6,
            "opponent": "Verona FC",
            "date": "2026-11-08",
        },
        {
            "id": 7,
            "opponent": "Portmanock FC",
            "date": "2026-11-15",
        },
        {
            "id": 8,
            "opponent": "Dunboyne FC",
            "date": "2026-12-06",
        },
    ]


def test_explicit_fixture_id(fixtures):
    assert (
        resolve_fixture(
            "Who is available for fixture 6?",
            fixtures,
        )
        == 6
    )


def test_opponent_name(fixtures):
    assert (
        resolve_fixture(
            "Who is available for Verona?",
            fixtures,
        )
        == 6
    )


def test_full_opponent_name(fixtures):
    assert (
        resolve_fixture(
            "Generate squads for Portmanock FC",
            fixtures,
        )
        == 7
    )


def test_follow_up_uses_current_fixture(fixtures):
    assert (
        resolve_fixture(
            "Generate squads",
            fixtures,
            current_fixture_id=6,
        )
        == 6
    )


def test_explicit_fixture_switch(fixtures):
    assert (
        resolve_fixture(
            "Who is available for fixture 7?",
            fixtures,
            current_fixture_id=6,
        )
        == 7
    )


def test_unknown_fixture(fixtures):
    with pytest.raises(
        ValueError,
        match="Fixture 999 does not exist",
    ):
        resolve_fixture(
            "Generate squads for fixture 999",
            fixtures,
        )


def test_ambiguous_opponent(fixtures):
    with pytest.raises(
        ValueError,
        match="Multiple fixtures match",
    ):
        resolve_fixture(
            "Generate squads for Dunboyne",
            fixtures,
        )


def test_no_fixture_selected(fixtures):
    assert (
        resolve_fixture(
            "Who is available?",
            fixtures,
        )
        is None
    )


def test_extract_explicit_fixture_id():
    assert extract_explicit_fixture_id("fixture ID 12") == 12
