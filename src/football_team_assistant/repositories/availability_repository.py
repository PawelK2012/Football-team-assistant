from psycopg.rows import DictRow

from football_team_assistant.db.database import admin_connection
from football_team_assistant.repositories.admin_records import RecordMissing


def get_roster(fixture_id: int) -> list[DictRow]:
    with admin_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.id AS player_id, p.name, a.available
            FROM fixtures f
            LEFT JOIN players p ON TRUE
            LEFT JOIN availability a ON a.fixture_id = f.id AND a.player_id = p.id
            WHERE f.id = %s
            ORDER BY p.name, p.id
            """,
            (fixture_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        raise RecordMissing("Fixture", fixture_id)
    return [row for row in rows if row["player_id"] is not None]


def save_batch(fixture_id: int, changes: dict[int, bool]) -> None:
    player_ids = sorted(changes)
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM fixtures WHERE id = %s FOR KEY SHARE", (fixture_id,))
        if cursor.fetchone() is None:
            raise RecordMissing("Fixture", fixture_id)

        cursor.execute(
            "SELECT id FROM players WHERE id = ANY(%s) ORDER BY id FOR KEY SHARE",
            (player_ids,),
        )
        found = {row["id"] for row in cursor.fetchall()}
        for player_id in player_ids:
            if player_id not in found:
                raise RecordMissing("Player", player_id)

        cursor.executemany(
            """
            INSERT INTO availability (fixture_id, player_id, available)
            VALUES (%s, %s, %s)
            ON CONFLICT (fixture_id, player_id) DO UPDATE SET available = EXCLUDED.available
            """,
            [(fixture_id, player_id, changes[player_id]) for player_id in player_ids],
        )
