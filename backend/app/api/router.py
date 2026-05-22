from fastapi import APIRouter, Depends

from backend.app.api.routes import admin, games, imports, meetups, users
from backend.app.core.security import verify_internal_api_token

api_router = APIRouter(dependencies=[Depends(verify_internal_api_token)])
api_router.include_router(users.router)
api_router.include_router(games.router)
api_router.include_router(meetups.router)
api_router.include_router(imports.router)
api_router.include_router(admin.router)
