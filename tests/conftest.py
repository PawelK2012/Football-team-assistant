import os

import pytest

from football_team_assistant.db.database import get_connection

TEST_DATABASE_URL = "postgresql://football:football@localhost:5432/football_assistant_test"


@pytest.fixture(scope="session", autouse=True)
def configure_test_database():
    original_url = os.environ.get("DATABASE_URL")

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    yield

    if original_url is None:
        os.environ.pop(
            "DATABASE_URL",
            None,
        )
    else:
        os.environ["DATABASE_URL"] = original_url


@pytest.fixture
def clean_database():
    with get_connection() as connection:
        database_name = connection.info.dbname

        if not database_name.endswith("_test"):
            raise RuntimeError(f"Refusing to clean non-test database: {database_name}")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    goalkeeper_history,
                    availability,
                    fixtures,
                    players
                RESTART IDENTITY CASCADE
                """
            )

    yield
