from db.database import get_connection


def get_fixtures() -> list[dict]:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    id,
                    fixture_date,
                    opponent,
                    home
                FROM fixtures
                ORDER BY fixture_date
                """
        )

        rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "date": row[1].isoformat(),
            "opponent": row[2],
            "home": row[3],
        }
        for row in rows
    ]


def get_fixture(fixture_id: int) -> dict | None:
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    id,
                    fixture_date,
                    opponent,
                    home
                FROM fixtures
                WHERE id = %s
                """,
            (fixture_id,),
        )

        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "date": row[1].isoformat(),
        "opponent": row[2],
        "home": row[3],
    }