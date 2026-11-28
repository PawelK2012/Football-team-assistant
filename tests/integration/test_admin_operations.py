from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from typing import Literal

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import DictRow

from football_team_assistant.db.database import get_connection
from football_team_assistant.repositories.player_repository import get_available_players
from football_team_assistant.services import admin_service
from tests.api.test_web_admin import ORIGIN, browser

PLAYERS = "/admin/api/players"
FIXTURES = "/admin/api/fixtures"


def create_player(name: str) -> int:
    return admin_service.create_player(admin_service.NewPlayer(name=name, rating=3.5))["id"]


def create_fixture(opponent: str) -> int:
    return admin_service.create_fixture(
        admin_service.FixtureFields(date="2026-11-28", opponent=opponent, home=True)
    )["id"]


def availability_url(fixture_id: int) -> str:
    return f"{FIXTURES}/{fixture_id}/availability"


def wait_for_blocked_transaction(blocker_pid: int) -> None:
    deadline = monotonic() + 3
    with get_connection() as inspector:
        inspector.autocommit = True
        while monotonic() < deadline:
            row = inspector.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM pg_stat_activity
                    WHERE datname = current_database()
                    AND %s = ANY(pg_blocking_pids(pid))
                )
                """,
                (blocker_pid,),
            ).fetchone()
            if row and row[0]:
                return
            sleep(0.02)
    pytest.fail("The concurrent admin operation did not wait for the parent lock.")


def test_availability_batch_persists_and_isolates_changes(clean_database: None) -> None:
    first = create_player("First")
    second = create_player("Second")
    untouched = create_player("Untouched")
    fixture = create_fixture("First FC")
    other = create_fixture("Second FC")
    with browser() as client:
        url = availability_url(fixture)
        other_url = availability_url(other)
        assert client.get(url).json() == {
            "fixture_id": fixture,
            "players": [
                {"player_id": first, "name": "First", "available": None},
                {"player_id": second, "name": "Second", "available": None},
                {"player_id": untouched, "name": "Untouched", "available": None},
            ],
        }
        for endpoint in (url, other_url):
            assert (
                client.put(
                    endpoint,
                    headers=ORIGIN,
                    json={"changes": [{"player_id": first, "available": True}]},
                ).status_code
                == 200
            )

        changes = [
            {"player_id": first, "available": False},
            {"player_id": second, "available": True},
        ]
        for _ in range(2):
            response = client.put(url, headers=ORIGIN, json={"changes": changes})
            assert response.json() == {"fixture_id": fixture, "changes": changes}
        assert [row["available"] for row in client.get(url).json()["players"]] == [
            False,
            True,
            None,
        ]
        assert [row["available"] for row in client.get(other_url).json()["players"]] == [
            True,
            None,
            None,
        ]
    assert [player["id"] for player in get_available_players(fixture)] == [second]


def test_storage_error_rolls_back_batch_after_first_write(clean_database: None) -> None:
    first = create_player("First")
    second = create_player("Second")
    fixture = create_fixture("Test FC")
    with get_connection() as connection:
        connection.execute(
            sql.SQL(
                "ALTER TABLE availability ADD CONSTRAINT admin_test_reject_second "
                "CHECK (player_id <> {} OR available = FALSE)"
            ).format(sql.Literal(second))
        )
    try:
        with browser() as client:
            url = availability_url(fixture)
            response = client.put(
                url,
                headers=ORIGIN,
                json={
                    "changes": [
                        {"player_id": first, "available": True},
                        {"player_id": second, "available": True},
                    ]
                },
            )
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "storage_unavailable"
            assert [row["available"] for row in client.get(url).json()["players"]] == [None, None]
    finally:
        with get_connection() as connection:
            connection.execute("ALTER TABLE availability DROP CONSTRAINT admin_test_reject_second")


def test_manage_players_and_fixtures_and_preserve_links(clean_database: None) -> None:
    with browser() as client:
        player_data = {"name": " First ", "rating": 3.5, "can_play_goalkeeper": True}
        fixture_data = {"date": "2026-11-28", "opponent": " Test FC ", "home": False}
        player = client.post(PLAYERS, headers=ORIGIN, json=player_data).json()
        fixture = client.post(FIXTURES, headers=ORIGIN, json=fixture_data).json()
        player_url = f"{PLAYERS}/{player['id']}"
        fixture_url = f"{FIXTURES}/{fixture['id']}"
        availability = availability_url(fixture["id"])
        assert player["name"] == "First"
        assert fixture["opponent"] == "Test FC"
        assert (
            client.put(
                availability,
                headers=ORIGIN,
                json={"changes": [{"player_id": player["id"], "available": True}]},
            ).status_code
            == 200
        )
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO goalkeeper_history (fixture_id, player_id) VALUES (%s, %s)",
                (fixture["id"], player["id"]),
            )
        player_data.update(name="Renamed", rating=4.5)
        fixture_data.update(opponent="Other FC", date="2026-12-01", home=True)
        assert client.put(player_url, headers=ORIGIN, json=player_data).json() == {
            "id": player["id"],
            **player_data,
        }
        assert client.put(fixture_url, headers=ORIGIN, json=fixture_data).json() == {
            "id": fixture["id"],
            **fixture_data,
        }
        assert client.get(PLAYERS).json() == [{"id": player["id"], **player_data}]
        assert client.get(FIXTURES).json() == [{"id": fixture["id"], **fixture_data}]
        assert client.get(availability).json()["players"][0]["available"] is True
        for url in (player_url, fixture_url):
            response = client.post(url + "/delete", headers=ORIGIN, json={"confirmed": True})
            assert response.json()["error"]["code"] == "goalkeeper_history_exists"
            assert response.status_code == 409


@pytest.mark.parametrize("target", ["players", "fixtures"])
def test_batch_rejects_record_deleted_while_save_waits(
    clean_database: None, target: Literal["players", "fixtures"]
) -> None:
    fixture = create_fixture("Test FC")
    first = create_player("First")
    second = create_player("Second")
    record = first if target == "players" else fixture
    changes = [{"player_id": first, "available": True}, {"player_id": second, "available": True}]
    with browser() as client, ThreadPoolExecutor(max_workers=1) as pool:
        with get_connection() as deleting:
            deleting.execute(
                sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(target)), (record,)
            )
            future = pool.submit(
                client.put, availability_url(fixture), headers=ORIGIN, json={"changes": changes}
            )
            wait_for_blocked_transaction(deleting.info.backend_pid)
        response = future.result(timeout=5)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "record_missing"
    assert get_available_players(fixture) == []


@pytest.mark.parametrize("target", ["players", "fixtures"])
def test_delete_waits_for_save_and_then_cascades(
    clean_database: None, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = create_fixture("Test FC")
    player = create_player("Player")
    record = player if target == "players" else fixture
    original_commit = psycopg.Connection.commit
    ready_to_commit = Event()
    allow_commit = Event()
    saver_pid: list[int] = []

    def pause_first_commit(connection: psycopg.Connection[DictRow]) -> None:
        if not ready_to_commit.is_set():
            saver_pid.append(connection.info.backend_pid)
            ready_to_commit.set()
            if not allow_commit.wait(timeout=5):
                raise TimeoutError("The competing delete did not reach the lock.")
        original_commit(connection)

    monkeypatch.setattr(psycopg.Connection, "commit", pause_first_commit)
    with browser() as client, ThreadPoolExecutor(max_workers=2) as pool:
        saving = pool.submit(
            client.put,
            availability_url(fixture),
            headers=ORIGIN,
            json={"changes": [{"player_id": player, "available": True}]},
        )
        try:
            assert ready_to_commit.wait(timeout=5)
            deleting = pool.submit(
                client.post,
                f"/admin/api/{target}/{record}/delete",
                headers=ORIGIN,
                json={"confirmed": True},
            )
            wait_for_blocked_transaction(saver_pid[0])
        finally:
            allow_commit.set()
        assert saving.result(timeout=5).status_code == 200
        assert deleting.result(timeout=5).status_code == 204
        assert client.get(f"/admin/api/{target}").json() == []
        assert get_available_players(fixture) == []


@pytest.mark.parametrize("target", ["players", "fixtures"])
def test_delete_sees_history_committed_while_waiting_for_parent(
    clean_database: None, target: str
) -> None:
    fixture = create_fixture("Test FC")
    player = create_player("Player")
    record = player if target == "players" else fixture
    with browser() as client, ThreadPoolExecutor(max_workers=1) as pool:
        with get_connection() as assigning:
            assigning.execute(
                "INSERT INTO goalkeeper_history (fixture_id, player_id) VALUES (%s, %s)",
                (fixture, player),
            )
            future = pool.submit(
                client.post,
                f"/admin/api/{target}/{record}/delete",
                headers=ORIGIN,
                json={"confirmed": True},
            )
            wait_for_blocked_transaction(assigning.info.backend_pid)
        assert future.result(timeout=5).status_code == 409
        assert client.get(f"/admin/api/{target}").json()[0]["id"] == record


def test_lost_commit_acknowledgment_reports_unknown_outcome(
    clean_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_commit = psycopg.Connection.commit

    def lose_acknowledgment(connection: psycopg.Connection[DictRow]) -> None:
        original_commit(connection)
        raise psycopg.OperationalError("commit acknowledgment lost")

    with browser() as client:
        with monkeypatch.context() as commit_failure:
            commit_failure.setattr(psycopg.Connection, "commit", lose_acknowledgment)
            response = client.post(
                PLAYERS, headers=ORIGIN, json={"name": "Saved once", "rating": 3.5}
            )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "outcome_unknown"
        assert [player["name"] for player in client.get(PLAYERS).json()] == ["Saved once"]
