import os

import psycopg
from dotenv import load_dotenv


load_dotenv(
    override=True,
)


def get_connection():
    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    return psycopg.connect(
        database_url
    )