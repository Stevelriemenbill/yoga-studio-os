from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _range(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    if end is None:
        end = datetime.now()
    if start is None:
        start = end - timedelta(days=30)
    return start, end


@router.get("/pulse")
async def community_pulse(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Sanfter Puls der Gemeinschaft – wie viele Menschen praktizieren gerade."""
    start, end = _range(start, end)
    return await analytics_service.community_pulse(db, current.tenant_id, start, end)


@router.get("/teachers")
async def teachers(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Reichweite der Lehrenden: begleitete und wiederkehrende Schüler:innen."""
    start, end = _range(start, end)
    return await analytics_service.teacher_reach(db, current.tenant_id, start, end)
