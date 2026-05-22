from fastapi import Header, HTTPException, status

from backend.app.core.config import get_settings


def verify_internal_api_token(x_internal_token: str = Header(...)) -> None:
    settings = get_settings()
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API token.",
        )
