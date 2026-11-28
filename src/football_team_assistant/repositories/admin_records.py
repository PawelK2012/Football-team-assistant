from typing import Literal

from psycopg import sql

from football_team_assistant.db.database import admin_connection

RecordTable = Literal["players", "fixtures"]


class RecordMissing(Exception):
    def __init__(self, record_type: str, record_id: int) -> None:
        super().__init__(f"{record_type} #{record_id} no longer exists.")


class GoalkeeperHistoryExists(Exception):
    """A linked goalkeeper assignment protects the record from deletion."""


def delete_record(table: RecordTable, record_id: int) -> None:
    table_name = sql.Identifier(table)
    record_type, history_key = (
        ("Player", "player_id") if table == "players" else ("Fixture", "fixture_id")
    )
    with admin_connection(write=True) as connection, connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT id FROM {} WHERE id = %s FOR UPDATE").format(table_name),
            (record_id,),
        )
        if cursor.fetchone() is None:
            raise RecordMissing(record_type, record_id)

        cursor.execute(
            sql.SQL("SELECT 1 FROM goalkeeper_history WHERE {} = %s LIMIT 1").format(
                sql.Identifier(history_key)
            ),
            (record_id,),
        )
        if cursor.fetchone() is not None:
            raise GoalkeeperHistoryExists

        cursor.execute(sql.SQL("DELETE FROM {} WHERE id = %s").format(table_name), (record_id,))
