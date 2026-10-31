from fastapi import (
    APIRouter,
    HTTPException,
)

from api.models.squad import SquadResult
from services.match_service import (
    create_match_squads,
)

router = APIRouter(
    prefix="/fixtures",
    tags=["squads"],
)


@router.post(
    "/{fixture_id}/squads",
    response_model=SquadResult,
)
def generate_squads(
    fixture_id: int,
):
    try:
        return create_match_squads(fixture_id)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
