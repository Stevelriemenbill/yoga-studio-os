import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_staff
from app.db.session import get_db
from app.models.checkin import CheckInMethod
from app.models.member import Member
from app.models.session import CourseSession
from app.models.user import STAFF_ROLES
from app.schemas.checkin import (
    AttendanceConfirm,
    AttendanceRead,
    AttendanceSet,
    CheckInRead,
    ManualCheckInRequest,
    MemberPassRead,
    QRCheckInRequest,
)
from app.services import checkin as checkin_service
from app.services.checkin import (
    AttendanceRepository,
    CheckInError,
    member_qr_token,
    verify_qr_token,
)

router = APIRouter(prefix="/checkin", tags=["checkin"])
attendance_router = APIRouter(prefix="/attendance", tags=["attendance"])


async def _get_session(db, tenant_id, session_id) -> CourseSession:
    session = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id, CourseSession.id == session_id
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _get_member(db, tenant_id, member_id) -> Member:
    member = (
        await db.execute(
            select(Member).where(Member.tenant_id == tenant_id, Member.id == member_id)
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/pass/{member_id}", response_model=MemberPassRead)
async def get_member_pass(
    member_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the signed QR token for a member's digital pass / wallet."""
    member = await _get_member(db, current.tenant_id, member_id)
    token = member_qr_token(current.tenant_id, member.id)
    return MemberPassRead(
        member_id=member.id,
        token=token,
        qr_payload=f"studioos://checkin?token={token}",
    )


@router.post("/qr", response_model=CheckInRead, status_code=status.HTTP_201_CREATED)
async def qr_check_in(
    data: QRCheckInRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member_id = verify_qr_token(current.tenant_id, data.token)
    if member_id is None:
        raise HTTPException(status_code=400, detail="Invalid QR token")
    session = await _get_session(db, current.tenant_id, data.session_id)
    member = await _get_member(db, current.tenant_id, member_id)
    # Self check-in by a member/trainee needs staff confirmation to count.
    requires_confirmation = current.role not in STAFF_ROLES
    try:
        return await checkin_service.check_in(
            db,
            current.tenant_id,
            session,
            member,
            method=CheckInMethod.QR,
            device_id=data.device_id,
            requires_confirmation=requires_confirmation,
        )
    except CheckInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/manual", response_model=CheckInRead, status_code=status.HTTP_201_CREATED)
async def manual_check_in(
    data: ManualCheckInRequest,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session(db, current.tenant_id, data.session_id)
    member = await _get_member(db, current.tenant_id, data.member_id)
    try:
        return await checkin_service.check_in(
            db,
            current.tenant_id,
            session,
            member,
            method=CheckInMethod.MANUAL,
            device_id=data.device_id,
        )
    except CheckInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@attendance_router.get("/session/{session_id}", response_model=list[AttendanceRead])
async def list_attendance(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AttendanceRepository(db, current.tenant_id).for_session(session_id)


@attendance_router.get("/pending", response_model=list[AttendanceRead])
async def list_pending(
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """All self check-ins awaiting staff confirmation across sessions."""
    return await AttendanceRepository(db, current.tenant_id).pending()


@attendance_router.post(
    "/session/{session_id}/confirm", response_model=AttendanceRead
)
async def confirm_attendance(
    session_id: uuid.UUID,
    data: AttendanceConfirm,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session(db, current.tenant_id, session_id)
    await _get_member(db, current.tenant_id, data.member_id)
    try:
        return await checkin_service.confirm_attendance(
            db, current.tenant_id, session, data.member_id, current.user.id
        )
    except CheckInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@attendance_router.post(
    "/session/{session_id}/reject", response_model=AttendanceRead
)
async def reject_attendance(
    session_id: uuid.UUID,
    data: AttendanceConfirm,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    await _get_session(db, current.tenant_id, session_id)
    await _get_member(db, current.tenant_id, data.member_id)
    try:
        return await checkin_service.reject_attendance(
            db, current.tenant_id, session_id, data.member_id, current.user.id
        )
    except CheckInError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@attendance_router.put("/session/{session_id}", response_model=AttendanceRead)
async def set_attendance(
    session_id: uuid.UUID,
    data: AttendanceSet,
    current: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    await _get_session(db, current.tenant_id, session_id)
    await _get_member(db, current.tenant_id, data.member_id)
    return await checkin_service.set_attendance(
        db,
        current.tenant_id,
        session_id,
        data.member_id,
        data.status,
        recorded_by=current.user.id,
    )
