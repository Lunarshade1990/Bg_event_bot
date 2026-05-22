from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models.bgg_import_job import BggImportJob
from backend.app.db.models.enums import ImportJobStatus, OwnershipSource
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def create_import_job(db: Session, *, user_id: int, bgg_username: str) -> BggImportJob:
    job = BggImportJob(
        user_id=user_id,
        bgg_username=bgg_username,
        status=ImportJobStatus.PENDING,
        imported_count=0,
    )
    db.add(job)
    db.flush()
    return job


def mark_import_job_in_progress(db: Session, job: BggImportJob) -> None:
    job.status = ImportJobStatus.IN_PROGRESS
    job.started_at = datetime.now(timezone.utc)
    db.flush()


def mark_import_job_completed(db: Session, job: BggImportJob, *, imported_count: int) -> None:
    job.status = ImportJobStatus.COMPLETED
    job.imported_count = imported_count
    job.finished_at = datetime.now(timezone.utc)
    job.error_message = None
    db.flush()


def mark_import_job_failed(db: Session, job: BggImportJob, *, error_message: str) -> None:
    job.status = ImportJobStatus.FAILED
    job.finished_at = datetime.now(timezone.utc)
    job.error_message = error_message
    db.flush()


def get_user_game(db: Session, *, user_id: int, game_id: int) -> UserGame | None:
    stmt = select(UserGame).where(UserGame.user_id == user_id, UserGame.game_id == game_id)
    return db.scalar(stmt)


def create_user_game(
    db: Session,
    *,
    user_id: int,
    game_id: int,
    source: OwnershipSource,
    is_available_for_meetups: bool = True,
) -> UserGame:
    user_game = UserGame(
        user_id=user_id,
        game_id=game_id,
        source=source,
        is_available_for_meetups=is_available_for_meetups,
    )
    db.add(user_game)
    db.flush()
    return user_game


def update_user_bgg_username(db: Session, *, user: User, bgg_username: str) -> None:
    user.bgg_username = bgg_username
    db.flush()
