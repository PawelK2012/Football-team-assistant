from football_team_assistant.db.database import get_connection
from football_team_assistant.services.match_service import (
    create_match_squads,
)


def test_create_match_squads(clean_database):
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

        players = [
            ("P1", 6.0, True),
            ("P2", 5.5, True),
            ("P3", 5.0, False),
            ("P4", 4.5, False),
            ("P5", 4.0, False),
            ("P6", 4.0, False),
            ("P7", 3.5, False),
            ("P8", 3.0, False),
            ("P9", 2.5, False),
            ("P10", 2.0, False),
        ]

        player_ids = []

        for name, rating, goalkeeper in players:
            cursor.execute(
                """
                    INSERT INTO players (
                        name,
                        rating,
                        can_play_goalkeeper
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                (
                    name,
                    rating,
                    goalkeeper,
                ),
            )

            player_ids.append(cursor.fetchone()[0])

        for player_id in player_ids:
            cursor.execute(
                """
                    INSERT INTO availability (
                        fixture_id,
                        player_id,
                        available
                    )
                    VALUES (%s, %s, TRUE)
                    """,
                (
                    fixture_id,
                    player_id,
                ),
            )

    result = create_match_squads(fixture_id)

    assert result["fixture"]["opponent"] == ("Raheny United")

    assert len(result["squad_a"]) == 5
    assert len(result["squad_b"]) == 5

    all_selected_ids = {player["id"] for player in (result["squad_a"] + result["squad_b"])}

    assert all_selected_ids == set(player_ids)

    assert result["goalkeeper_a"]["can_play_goalkeeper"] is True

    assert result["goalkeeper_b"]["can_play_goalkeeper"] is True
