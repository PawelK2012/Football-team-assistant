from db.database import get_connection


def get_goalkeeper_history() -> list[dict]:

    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    f.fixture_date,
                    p.id,
                    p.name
                FROM goalkeeper_history gh
                JOIN fixtures f
                    ON f.id = gh.fixture_id
                JOIN players p
                    ON p.id = gh.player_id
                ORDER BY f.fixture_date, p.id
                """
        )

        rows = cursor.fetchall()

    return [
        {
            "date": row[0].isoformat(),
            "player_id": row[1],
            "player": row[2],
        }
        for row in rows
    ]