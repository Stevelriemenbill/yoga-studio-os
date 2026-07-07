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


@router.get("/kpis")
async def kpis(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    start, end = _range(start, end)
    return await analytics_service.studio_kpis(db, current.tenant_id, start, end)


@router.get("/heatmap")
async def heatmap(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    start, end = _range(start, end)
    return await analytics_service.heatmap(db, current.tenant_id, start, end)


@router.get("/teachers")
async def teachers(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    start, end = _range(start, end)
    return await analytics_service.teacher_analytics(db, current.tenant_id, start, end)


@router.get("/popular-courses")
async def popular_courses(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    start, end = _range(start, end)
    return await analytics_service.popular_courses(db, current.tenant_id, start, end)
