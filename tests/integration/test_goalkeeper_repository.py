from db.database import get_connection
from repositories.goalkeeper_repository import (
    get_goalkeeper_history,
)


def test_get_goalkeeper_history(
    clean_database,
):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                INSERT INTO players (
                    name,
                    rating,
                    can_play_goalkeeper
                )
                VALUES (
                    'Henry',
                    4.5,
                    TRUE
                )
                RETURNING id
                """
        )

        player_id = cursor.fetchone()[0]

        cursor.execute(
            """
                INSERT INTO fixtures (
                    fixture_date,
                    opponent,
                    home
                )
                VALUES (
                    '2026-09-20',
                    'Opponent',
                    FALSE
                )
                RETURNING id
                """
        )

        fixture_id = cursor.fetchone()[0]

        cursor.execute(
            """
                INSERT INTO goalkeeper_history (
                    fixture_id,
                    player_id
                )
                VALUES (%s, %s)
                """,
            (
                fixture_id,
                player_id,
            ),
        )

    history = get_goalkeeper_history()

    assert history == [
        {
            "date": "2026-09-20",
            "player_id": player_id,
            "player": "Henry",
        }
    ]
