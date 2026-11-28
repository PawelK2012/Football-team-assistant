import logging
from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import FastAPI, Request
from fastapi import Path as PathParameter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from psycopg.rows import DictRow
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from football_team_assistant.db.database import AdminWriteOutcomeUnknown, DatabaseConfigurationError
from football_team_assistant.repositories.admin_records import (
    GoalkeeperHistoryExists,
    RecordMissing,
)
from football_team_assistant.services import admin_service

HOST = "127.0.0.1:8002"
ORIGIN = f"http://{HOST}"
STATIC = Path(__file__).resolve().parent / "static"
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Football Admin Panel",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    redirect_slashes=False,
)
app.mount("/assets", StaticFiles(directory=STATIC.parents[1] / "static"), name="assets")


def failure(
    status: int, code: str, message: str, fields: dict[str, str] | None = None
) -> JSONResponse:
    error = {"code": code, "message": message}
    payload = {"error": {**error, "fields": fields} if fields else error}
    return JSONResponse(payload, status_code=status)


@app.middleware("http")
async def admin_boundary(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    writing = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    origins = request.headers.getlist("origin")
    if (
        request.client is None
        or request.client.host != "127.0.0.1"
        or request.headers.getlist("host") != [HOST]
        or ((writing or origins) and origins != [ORIGIN])
    ):
        response = failure(403, "access_denied", "Open the panel at the local admin address.")
    elif writing and not is_json(request):
        response = failure(415, "unsupported_content_type", "Send the request as JSON.")
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


def is_json(request: Request) -> bool:
    values = request.headers.getlist("content-type")
    return len(values) == 1 and values[0].partition(";")[0].strip().lower() == "application/json"


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, error: RequestValidationError) -> JSONResponse:
    fields = {
        ".".join(str(part) for part in entry["loc"][1:]): entry["msg"] for entry in error.errors()
    }
    return failure(422, "invalid_request", "Review the highlighted fields and try again.", fields)


@app.exception_handler(HTTPException)
async def route_error(_request: Request, error: HTTPException) -> JSONResponse:
    return failure(error.status_code, "invalid_request", "This admin request is unavailable.")


@app.exception_handler(DatabaseConfigurationError)
@app.exception_handler(psycopg.Error)
async def storage_unavailable(
    request: Request, _error: psycopg.Error | DatabaseConfigurationError
) -> JSONResponse:
    logger.warning("Admin %s: storage_unavailable", request.method)
    return failure(503, "storage_unavailable", "Saved data is unavailable. Try again.")


@app.exception_handler(AdminWriteOutcomeUnknown)
async def outcome_unknown(request: Request, _error: AdminWriteOutcomeUnknown) -> JSONResponse:
    logger.warning("Admin %s: outcome_unknown", request.method)
    return failure(503, "outcome_unknown", "The save could not be confirmed. Reload saved data.")


@app.get("/admin")
async def home() -> RedirectResponse:
    return RedirectResponse("/admin/players")


@app.get("/admin/availability")
@app.get("/admin/fixtures")
@app.get("/admin/players")
async def admin_page() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/admin/static/admin.css")
async def stylesheet() -> FileResponse:
    return FileResponse(STATIC / "admin.css", media_type="text/css")


@app.get("/admin/static/admin.js")
async def javascript() -> FileResponse:
    return FileResponse(STATIC / "admin.js", media_type="text/javascript")


@app.get("/admin/static/football-assistant.png")
async def brand_icon() -> FileResponse:
    return FileResponse(
        STATIC.parents[1] / "static" / "football-assistant.png", media_type="image/png"
    )


@app.get("/admin/static/tactics-wallpaper.png")
async def tactics_wallpaper() -> FileResponse:
    return FileResponse(
        STATIC.parents[1] / "static" / "tactics-wallpaper.png", media_type="image/png"
    )


class PlayerRecord(BaseModel):
    id: int
    name: str
    rating: float
    can_play_goalkeeper: bool


class FixtureRecord(BaseModel):
    id: int
    date: date
    opponent: str
    home: bool


@app.get("/admin/api/players", response_model=list[PlayerRecord])
def players() -> list[DictRow]:
    return admin_service.list_players()


@app.get("/admin/api/fixtures", response_model=list[FixtureRecord])
def fixtures() -> list[DictRow]:
    return admin_service.list_fixtures()


@app.exception_handler(RecordMissing)
async def record_missing(_request: Request, error: RecordMissing) -> JSONResponse:
    return failure(404, "record_missing", str(error))


@app.exception_handler(GoalkeeperHistoryExists)
async def history_exists(_request: Request, _error: GoalkeeperHistoryExists) -> JSONResponse:
    return failure(
        409,
        "goalkeeper_history_exists",
        "This record has goalkeeper history and cannot be deleted.",
    )


PathID = Annotated[int, PathParameter(gt=0, le=2_147_483_647)]


@app.get("/admin/api/fixtures/{fixture_id}/availability")
def availability(fixture_id: PathID) -> dict[str, int | list[DictRow]]:
    return {"fixture_id": fixture_id, "players": admin_service.get_availability(fixture_id)}


@app.put("/admin/api/fixtures/{fixture_id}/availability")
def save_availability(
    fixture_id: PathID, batch: admin_service.AvailabilityBatch
) -> dict[str, int | list[dict[str, int | bool]]]:
    return {"fixture_id": fixture_id, "changes": admin_service.save_availability(fixture_id, batch)}


@app.post("/admin/api/players", status_code=201, response_model=PlayerRecord)
def create_player(record: admin_service.NewPlayer) -> DictRow:
    return admin_service.create_player(record)


@app.put("/admin/api/players/{player_id}", response_model=PlayerRecord)
def update_player(player_id: PathID, record: admin_service.PlayerFields) -> DictRow:
    return admin_service.update_player(player_id, record)


@app.post("/admin/api/players/{player_id}/delete", status_code=204)
def delete_player(player_id: PathID, confirmation: admin_service.DeleteConfirmation) -> Response:
    admin_service.delete_player(player_id)
    return Response(status_code=204)


@app.post("/admin/api/fixtures", status_code=201, response_model=FixtureRecord)
def create_fixture(record: admin_service.FixtureFields) -> DictRow:
    return admin_service.create_fixture(record)


@app.put("/admin/api/fixtures/{fixture_id}", response_model=FixtureRecord)
def update_fixture(fixture_id: PathID, record: admin_service.FixtureFields) -> DictRow:
    return admin_service.update_fixture(fixture_id, record)


@app.post("/admin/api/fixtures/{fixture_id}/delete", status_code=204)
def delete_fixture(fixture_id: PathID, confirmation: admin_service.DeleteConfirmation) -> Response:
    admin_service.delete_fixture(fixture_id)
    return Response(status_code=204)
