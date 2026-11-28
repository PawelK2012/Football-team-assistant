from psycopg.rows import DictRow

from football_team_assistant.db.database import admin_connection, get_connection
from football_team_assistant.repositories.admin_records import RecordMissing


def get_available_players(
    fixture_id: int,
) -> list[dict]:

    with get_connection() as connection, connection.cursor() as cursor:
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


def list_admin_players() -> list[DictRow]:
    with admin_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, rating, can_play_goalkeeper FROM players ORDER BY name, id"
        )
        return cursor.fetchall()


def create_admin_player(name: str, rating: float, can_play_goalkeeper: bool) -> DictRow:
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO players (name, rating, can_play_goalkeeper)
            VALUES (%s, %s, %s)
            RETURNING id, name, rating, can_play_goalkeeper
            """,
            (name, rating, can_play_goalkeeper),
        )
        return cursor.fetchall()[0]


def update_admin_player(
    player_id: int, name: str, rating: float, can_play_goalkeeper: bool
) -> DictRow:
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE players SET name = %s, rating = %s, can_play_goalkeeper = %s
            WHERE id = %s
            RETURNING id, name, rating, can_play_goalkeeper
            """,
            (name, rating, can_play_goalkeeper, player_id),
        )
        record = cursor.fetchone()
        if record is None:
            raise RecordMissing("Player", player_id)
        return record
