from football_team_assistant.formatters import (
    format_available_players,
    format_squads,
)


def test_available_players_numbering():
    players = [
        {"id": 1, "name": "Henry", "rating": 4.5},
        {"id": 13, "name": "Cuan", "rating": 3.5},
        {"id": 14, "name": "Leo", "rating": 5.0},
    ]

    output = format_available_players(players)

    assert output.splitlines() == [
        "Available players (3):",
        "",
        "1. Henry (4.5)",
        "2. Cuan (3.5)",
        "3. Leo (5.0)",
    ]


def test_available_players_count():
    players = [
        {"id": 1, "name": "Henry", "rating": 4.5},
        {"id": 2, "name": "Sam", "rating": 4.5},
    ]

    output = format_available_players(players)

    assert "Available players (2)" in output


def test_empty_available_players():
    output = format_available_players([])

    assert "Available players (0)" in output


def test_squad_formatting(sample_squads):
    output = format_squads(sample_squads)

    assert "Squad A (3 players)" in output
    assert "Squad B (2 players)" in output

    assert "Goalkeeper: Jack" in output
    assert "Goalkeeper: Tom" in output

    assert "Jack (6.0) (GK)" in output
    assert "Tom (6.0) (GK)" in output

    assert "Balance difference: 0.75" in output
