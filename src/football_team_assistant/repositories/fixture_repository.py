from psycopg.rows import DictRow

from football_team_assistant.db.database import admin_connection, get_connection
from football_team_assistant.repositories.admin_records import RecordMissing


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


def list_admin_fixtures() -> list[DictRow]:
    with admin_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, fixture_date AS date, opponent, home FROM fixtures ORDER BY date, id"
        )
        return cursor.fetchall()


def create_admin_fixture(fixture_date: str, opponent: str, home: bool) -> DictRow:
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO fixtures (fixture_date, opponent, home)
            VALUES (%s, %s, %s)
            RETURNING id, fixture_date AS date, opponent, home
            """,
            (fixture_date, opponent, home),
        )
        return cursor.fetchall()[0]


def update_admin_fixture(fixture_id: int, fixture_date: str, opponent: str, home: bool) -> DictRow:
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE fixtures SET fixture_date = %s, opponent = %s, home = %s
            WHERE id = %s
            RETURNING id, fixture_date AS date, opponent, home
            """,
            (fixture_date, opponent, home, fixture_id),
        )
        record = cursor.fetchone()
        if record is None:
            raise RecordMissing("Fixture", fixture_id)
        return record
