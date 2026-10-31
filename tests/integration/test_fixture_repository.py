from football_team_assistant.db.database import get_connection
from football_team_assistant.repositories.fixture_repository import (
    get_fixture,
    get_fixtures,
)
from football_team_assistant.repositories.player_repository import (
    get_available_players,
)


def test_get_fixtures(clean_database):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO fixtures (
                    fixture_date,
                    opponent,
                    home
                )
                VALUES
                    ('2026-10-11', 'Dunboyne AFC', FALSE),
                    ('2026-10-18', 'Raheny United', TRUE)
                """
        )

    fixtures = get_fixtures()

    assert len(fixtures) == 2

    assert fixtures[0] == {
        "id": 1,
        "date": "2026-10-11",
        "opponent": "Dunboyne AFC",
        "home": False,
    }

    assert fixtures[1] == {
        "id": 2,
        "date": "2026-10-18",
        "opponent": "Raheny United",
        "home": True,
    }


def test_get_fixture(clean_database):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO fixtures (
                    fixture_date,
                    opponent,
                    home
                )
                VALUES (
                    '2026-10-18',
                    'Raheny United',
                    TRUE
                )
                RETURNING id
                """
        )

        fixture_id = cursor.fetchone()[0]

    fixture = get_fixture(fixture_id)

    assert fixture == {
        "id": fixture_id,
        "date": "2026-10-18",
        "opponent": "Raheny United",
        "home": True,
    }


def test_get_nonexistent_fixture_returns_none(
    clean_database,
):
    fixture = get_fixture(999)

    assert fixture is None


def test_get_available_players(
    clean_database,
):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO fixtures (
                    fixture_date,
                    opponent,
                    home
                )
                VALUES (
                    '2026-10-18',
                    'Raheny United',
                    TRUE
                )
                RETURNING id
                """
        )

        fixture_id = cursor.fetchone()[0]

        cursor.execute(
            """
                INSERT INTO players (
                    name,
                    rating,
                    can_play_goalkeeper
                )
                VALUES
                    ('Henry', 4.5, TRUE),
                    ('Sam', 5.0, TRUE),
                    ('Ben', 3.5, FALSE)
                RETURNING id
                """
        )

        player_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            """
                INSERT INTO availability (
                    fixture_id,
                    player_id,
                    available
                )
                VALUES
                    (%s, %s, TRUE),
                    (%s, %s, FALSE),
                    (%s, %s, TRUE)
                """,
            (
                fixture_id,
                player_ids[0],
                fixture_id,
                player_ids[1],
                fixture_id,
                player_ids[2],
            ),
        )

    players = get_available_players(fixture_id)

    assert len(players) == 2

    assert [player["name"] for player in players] == [
        "Henry",
        "Ben",
    ]
