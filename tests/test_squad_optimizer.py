import pytest

from football_team_assistant.squad_optimizer import (
    create_balanced_squads,
    select_goalkeeper,
)


@pytest.fixture
def players():
    return [
        {"id": 1, "name": "P1", "rating": 6.0, "can_play_goalkeeper": True},
        {"id": 2, "name": "P2", "rating": 5.5, "can_play_goalkeeper": True},
        {"id": 3, "name": "P3", "rating": 5.0, "can_play_goalkeeper": False},
        {"id": 4, "name": "P4", "rating": 4.5, "can_play_goalkeeper": False},
        {"id": 5, "name": "P5", "rating": 4.0, "can_play_goalkeeper": False},
        {"id": 6, "name": "P6", "rating": 4.0, "can_play_goalkeeper": False},
        {"id": 7, "name": "P7", "rating": 3.5, "can_play_goalkeeper": False},
        {"id": 8, "name": "P8", "rating": 3.0, "can_play_goalkeeper": False},
        {"id": 9, "name": "P9", "rating": 2.5, "can_play_goalkeeper": False},
        {"id": 10, "name": "P10", "rating": 2.0, "can_play_goalkeeper": False},
    ]


def test_creates_two_squads_using_every_player(players):
    result = create_balanced_squads(
        players,
        goalkeeper_history=[],
    )

    squad_a = result["squad_a"]
    squad_b = result["squad_b"]

    assert len(squad_a) == 5
    assert len(squad_b) == 5

    selected_ids = {player["id"] for player in squad_a + squad_b}

    assert selected_ids == {player["id"] for player in players}


def test_player_cannot_be_in_both_squads(players):
    result = create_balanced_squads(
        players,
        goalkeeper_history=[],
    )

    squad_a_ids = {player["id"] for player in result["squad_a"]}

    squad_b_ids = {player["id"] for player in result["squad_b"]}

    assert squad_a_ids.isdisjoint(squad_b_ids)


def test_each_squad_has_goalkeeper(players):
    result = create_balanced_squads(
        players,
        goalkeeper_history=[],
    )

    assert any(player["can_play_goalkeeper"] for player in result["squad_a"])

    assert any(player["can_play_goalkeeper"] for player in result["squad_b"])


def test_rejects_fewer_than_ten_players(players):
    with pytest.raises(
        ValueError,
        match="At least 10 available players",
    ):
        create_balanced_squads(
            players[:9],
            goalkeeper_history=[],
        )


@pytest.mark.parametrize(
    ("player_count", "expected_sizes"),
    [
        (10, (5, 5)),
        (11, (6, 5)),
        (12, (6, 6)),
        (13, (7, 6)),
        (14, (7, 7)),
        (15, (8, 7)),
        (16, (8, 8)),
    ],
)
def test_squad_sizes(
    player_count,
    expected_sizes,
):
    players = [
        {
            "id": i,
            "name": f"P{i}",
            "rating": 3.0,
            "can_play_goalkeeper": i <= 2,
        }
        for i in range(1, player_count + 1)
    ]

    result = create_balanced_squads(
        players,
        goalkeeper_history=[],
    )

    assert (
        len(result["squad_a"]),
        len(result["squad_b"]),
    ) == expected_sizes


def test_prefers_player_with_fewer_goalkeeper_appearances():
    players = [
        {
            "id": 1,
            "name": "Henry",
            "rating": 4.5,
            "can_play_goalkeeper": True,
        },
        {
            "id": 2,
            "name": "Sam",
            "rating": 4.5,
            "can_play_goalkeeper": True,
        },
    ]

    history = [
        {
            "date": "2026-09-20",
            "player_id": 1,
        },
        {
            "date": "2026-09-27",
            "player_id": 1,
        },
        {
            "date": "2026-09-20",
            "player_id": 2,
        },
    ]

    goalkeeper = select_goalkeeper(
        players,
        history,
    )

    assert goalkeeper["id"] == 2
