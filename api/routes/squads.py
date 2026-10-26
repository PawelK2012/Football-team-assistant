from fastapi import (
    APIRouter,
    HTTPException,
)

from services.match_service import (
    create_match_squads,
)

router = APIRouter(
    prefix="/fixtures",
    tags=["squads"],
)


@router.post("/{fixture_id}/squads")
def generate_squads(
    fixture_id: int,
):
    try:
        return create_match_squads(
            fixture_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error