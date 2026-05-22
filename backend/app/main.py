from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.logging import configure_logging
from backend.app.schemas.common import HealthCheck

configure_logging()

app = FastAPI(title="Boardgames Meetup Bot API", version="0.1.0")
app.include_router(api_router, prefix="/api")


@app.get("/health", response_model=HealthCheck, tags=["system"])
def healthcheck() -> HealthCheck:
    return HealthCheck(status="ok")
