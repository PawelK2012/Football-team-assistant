from fastapi import FastAPI

from api.routes.fixtures import (
    router as fixtures_router,
)
from api.routes.squads import (
    router as squads_router,
)

app = FastAPI(
    title="Football Team Assistant",
    version="0.1.0",
)

app.include_router(fixtures_router)
app.include_router(squads_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }
