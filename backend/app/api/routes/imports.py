from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies.db import get_db
from backend.app.schemas.import_job import BggCollectionImportRequest, BggCollectionImportResult
from backend.app.services.bgg_import import BggImportError, import_bgg_collection

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bgg/collection", response_model=BggCollectionImportResult)
def import_collection_from_bgg(
    payload: BggCollectionImportRequest,
    db: Session = Depends(get_db),
) -> BggCollectionImportResult:
    try:
        return import_bgg_collection(
            db,
            telegram_id=payload.telegram_id,
            bgg_username=payload.bgg_username,
        )
    except BggImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
