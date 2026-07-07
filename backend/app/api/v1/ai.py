from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.schemas.ai import AssistantQuery, InsightRead
from app.services import ai as ai_service
from app.services.ai import InsightRepository

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/insights", response_model=list[InsightRead])
async def list_insights(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await InsightRepository(db, current.tenant_id).list()


@router.post("/insights/generate", response_model=list[InsightRead])
async def generate_insights(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.generate_insights(db, current.tenant_id)


@router.get("/forecast")
async def forecast(
    days_ahead: int = 14,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.forecast_fill(db, current.tenant_id, days_ahead)


@router.post("/assistant", response_model=InsightRead)
async def assistant(
    query: AssistantQuery,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await ai_service.assistant_answer(db, current.tenant_id, query.question)
