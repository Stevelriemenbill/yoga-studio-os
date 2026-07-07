import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_staff
from app.db.session import get_db
from app.models.automation import AutomationRule
from app.schemas.automation import (
    AutomationRuleCreate,
    AutomationRuleRead,
    AutomationRuleUpdate,
    AutomationRunResult,
)
from app.services import automation as automation_service
from app.services.automation import AutomationRepository

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("", response_model=list[AutomationRuleRead])
async def list_rules(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await AutomationRepository(db, current.tenant_id).list()


@router.post("", response_model=AutomationRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule(
    data: AutomationRuleCreate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = AutomationRepository(db, current.tenant_id)
    rule = repo.add(AutomationRule(**data.model_dump()))
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AutomationRuleRead)
async def update_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    repo = AutomationRepository(db, current.tenant_id)
    rule = await repo.get(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.post("/run", response_model=AutomationRunResult)
async def run_all(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate all active batch rules (invoked by scheduler / manually)."""
    return await automation_service.run_all(db, current.tenant_id)
