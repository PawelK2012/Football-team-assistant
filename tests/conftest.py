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


@pytest.fixture
def sample_squads():
    return {
        "fixture": {
            "id": 6,
            "date": "2026-11-08",
            "opponent": "Verona FC",
            "home": True,
        },
        "squad_a": [
            {
                "id": 1,
                "name": "MrX",
                "rating": 4.5,
                "can_play_goalkeeper": True,
            },
            {
                "id": 2,
                "name": "MrY",
                "rating": 4.5,
                "can_play_goalkeeper": True,
            },
            {
                "id": 3,
                "name": "Orangutan",
                "rating": 6.0,
                "can_play_goalkeeper": True,
            },
        ],
        "squad_b": [
            {
                "id": 7,
                "name": "MBape",
                "rating": 6.0,
                "can_play_goalkeeper": True,
            },
            {
                "id": 8,
                "name": "Adele",
                "rating": 5.5,
                "can_play_goalkeeper": True,
            },
        ],
        "goalkeeper_a": {
            "id": 3,
            "name": "Johny",
            "rating": 6.0,
            "can_play_goalkeeper": True,
        },
        "goalkeeper_b": {
            "id": 7,
            "name": "Diebre",
            "rating": 6.0,
            "can_play_goalkeeper": True,
        },
        "average_rating_a": 5.0,
        "average_rating_b": 5.75,
        "balance_difference": 0.75,
    }
