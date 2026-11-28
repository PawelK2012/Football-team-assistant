import pytest
from fastapi.testclient import TestClient

from football_team_assistant.services import admin_service
from football_team_assistant.web_admin.app import app

BASE = "http://127.0.0.1:8002"
ORIGIN = {"Origin": BASE}


def browser() -> TestClient:
    return TestClient(app, base_url=BASE, client=("127.0.0.1", 12345))


def test_admin_serves_pages_and_assets() -> None:
    with browser() as client:
        response = client.get("/admin", follow_redirects=False)
        assert response.headers["location"] == "/admin/players"
        for page in ("players", "fixtures", "availability"):
            response = client.get(f"/admin/{page}")
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            assert "/admin/static/admin.js" in response.text
        for asset in ("admin.css", "admin.js"):
            assert client.get(f"/admin/static/{asset}").status_code == 200


def test_admin_requires_local_peer_host_and_write_origin() -> None:
    with TestClient(app, base_url=BASE, client=("192.0.2.5", 12345)) as client:
        assert client.get("/admin/players").status_code == 403
    with browser() as client:
        assert client.get("/admin/players", headers={"Host": "other:8002"}).status_code == 403
        duplicate = [("Host", "127.0.0.1:8002"), ("Host", "127.0.0.1:8002")]
        assert client.get("/admin/players", headers=duplicate).status_code == 403
        foreign_origin = {"Origin": "https://example.invalid"}
        response = client.get("/admin/players", headers=foreign_origin)
        assert response.status_code == 403
        endpoint = "/admin/api/fixtures/1/availability"
        assert client.put(endpoint, json={}).status_code == 403
        assert client.put(endpoint, headers=ORIGIN, content="{}").status_code == 415


def test_admin_lists_preserve_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin_service, "list_players", lambda: [])
    monkeypatch.setattr(admin_service, "list_fixtures", lambda: [])
    with browser() as client:
        for collection in ("players", "fixtures"):
            assert client.get(f"/admin/api/{collection}").json() == []


def test_availability_returns_roster_and_persists_a_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    changes = [{"player_id": 2, "available": True}, {"player_id": 5, "available": False}]

    def save(
        fixture_id: int, batch: admin_service.AvailabilityBatch
    ) -> list[dict[str, int | bool]]:
        assert fixture_id == 8
        assert [change.model_dump() for change in batch.changes] == changes
        return changes

    monkeypatch.setattr(admin_service, "save_availability", save, raising=False)
    monkeypatch.setattr(
        admin_service,
        "get_availability",
        lambda fixture_id: [{"player_id": fixture_id, "name": "Test", "available": None}],
        raising=False,
    )
    with browser() as client:
        url = "/admin/api/fixtures/8/availability"
        assert client.get(url).json() == {
            "fixture_id": 8,
            "players": [{"player_id": 8, "name": "Test", "available": None}],
        }
        assert client.put(url, headers=ORIGIN, json={"changes": changes}).json() == {
            "fixture_id": 8,
            "changes": changes,
        }
        for invalid in ([], changes * 2, [{"player_id": 2, "available": 1}]):
            response = client.put(url, headers=ORIGIN, json={"changes": invalid})
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "invalid_request"


def test_player_and_fixture_validation_and_confirmed_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_service,
        "create_player",
        lambda record: {"id": 1, **record.model_dump()},
        raising=False,
    )
    monkeypatch.setattr(
        admin_service,
        "update_fixture",
        lambda fixture_id, record: {"id": fixture_id, **record.model_dump()},
        raising=False,
    )
    deleted = []
    monkeypatch.setattr(admin_service, "delete_player", deleted.append, raising=False)
    with browser() as client:
        players = "/admin/api/players"
        fixtures = "/admin/api/fixtures"
        created = client.post(players, headers=ORIGIN, json={"name": "  Jo ", "rating": 3.5})
        assert created.status_code == 201
        assert created.json() == {
            "id": 1,
            "name": "Jo",
            "rating": 3.5,
            "can_play_goalkeeper": False,
        }
        assert (
            client.post(players, headers=ORIGIN, json={"name": "Jo", "rating": 3.51}).status_code
            == 422
        )
        valid = {"date": "2026-11-28", "opponent": " Away FC ", "home": False}
        assert client.put(f"{fixtures}/2", headers=ORIGIN, json=valid).json() == {
            "id": 2,
            "date": "2026-11-28",
            "opponent": "Away FC",
            "home": False,
        }
        assert (
            client.put(
                f"{fixtures}/2",
                headers=ORIGIN,
                json={**valid, "date": "2026-02-30"},
            ).status_code
            == 422
        )
        deletion = f"{players}/1/delete"
        assert client.post(deletion, headers=ORIGIN, json={"confirmed": False}).status_code == 422
        assert client.post(deletion, headers=ORIGIN, json={"confirmed": True}).status_code == 204
        assert deleted == [1]
