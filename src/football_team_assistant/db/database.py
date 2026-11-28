import os
from collections.abc import Iterator
from contextlib import closing, contextmanager

import psycopg
from dotenv import load_dotenv
from psycopg.rows import DictRow, TupleRow, dict_row

load_dotenv(
    override=True,
)


class DatabaseConfigurationError(RuntimeError):
    """The database connection has not been configured."""


def database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise DatabaseConfigurationError("DATABASE_URL environment variable is not set.")

    return database_url


def get_connection() -> psycopg.Connection[TupleRow]:
    return psycopg.connect(database_url())


class AdminWriteOutcomeUnknown(Exception):
    """The connection failed while PostgreSQL was confirming the commit."""


@contextmanager
def admin_connection(*, write: bool = False) -> Iterator[psycopg.Connection[DictRow]]:
    with closing(
        psycopg.Connection[DictRow].connect(
            database_url(),
            connect_timeout=3,
            options="-c statement_timeout=5000 -c transaction_timeout=10000",
            row_factory=dict_row,
        )
    ) as connection:
        connection.isolation_level = psycopg.IsolationLevel.READ_COMMITTED
        yield connection
        if write:
            try:
                connection.commit()
            except psycopg.OperationalError as error:
                raise AdminWriteOutcomeUnknown from error
