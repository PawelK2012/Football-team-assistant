from db.database import get_connection


def get_available_players(
    fixture_id: int,
) -> list[dict]:

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.rating,
                    p.can_play_goalkeeper
                FROM availability a
                JOIN players p
                    ON p.id = a.player_id
                WHERE a.fixture_id = %s
                  AND a.available = TRUE
                ORDER BY p.id
                """,
                (fixture_id,),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "rating": float(row[2]),
            "can_play_goalkeeper": row[3],
        }
        for row in rows
    ]