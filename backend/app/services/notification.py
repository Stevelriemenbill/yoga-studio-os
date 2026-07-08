import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.member import Member
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.models.session import CourseSession
from app.services.channels import get_sender
from app.services.weather import WeatherForecast, weather_advice


class NotificationRepository(TenantRepository[Notification]):
    model = Notification

    async def pending(self, limit: int = 100) -> list[Notification]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            self._base_query()
            .where(Notification.status == NotificationStatus.PENDING)
            .where(
                (Notification.scheduled_for.is_(None))
                | (Notification.scheduled_for <= now)
            )
            .limit(limit)
        )
        return list(result.scalars().all())


async def enqueue(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    channel: NotificationChannel,
    body: str,
    member_id: uuid.UUID | None = None,
    subject: str | None = None,
    scheduled_for: datetime | None = None,
    template: str | None = None,
    recipient_email: str | None = None,
) -> Notification:
    repo = NotificationRepository(db, tenant_id)
    notification = repo.add(
        Notification(
            member_id=member_id,
            channel=channel,
            subject=subject,
            body=body,
            scheduled_for=scheduled_for,
            template=template,
            status=NotificationStatus.PENDING,
        )
    )
    await db.commit()
    await db.refresh(notification)
    # Transient (non-persisted) recipient address used by real email senders.
    if recipient_email is not None:
        notification.recipient_email = recipient_email
    return notification


async def _resolve_recipient_email(
    db: AsyncSession, notification: Notification
) -> str | None:
    """Best-effort resolve an email address for an EMAIL notification."""
    existing = getattr(notification, "recipient_email", None)
    if existing:
        return existing
    if notification.member_id is not None:
        member = (
            await db.execute(
                select(Member).where(Member.id == notification.member_id)
            )
        ).scalar_one_or_none()
        if member and member.email:
            return member.email
    return None


async def deliver(db: AsyncSession, notification: Notification) -> Notification:
    try:
        if notification.channel == NotificationChannel.EMAIL:
            notification.recipient_email = await _resolve_recipient_email(
                db, notification
            )
        await get_sender(notification.channel).send(notification)
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(UTC)
        notification.error = None
    except Exception as exc:  # noqa: BLE001 - record any provider failure
        notification.status = NotificationStatus.FAILED
        notification.error = str(exc)[:500]
    await db.commit()
    await db.refresh(notification)
    return notification


async def process_pending(
    db: AsyncSession, tenant_id: uuid.UUID, limit: int = 100
) -> int:
    """Deliver all due pending notifications for a tenant. Returns count sent."""
    repo = NotificationRepository(db, tenant_id)
    pending = await repo.pending(limit=limit)
    sent = 0
    for n in pending:
        result = await deliver(db, n)
        if result.status == NotificationStatus.SENT:
            sent += 1
    return sent


def compose_smart_reminder(
    *,
    course_name: str,
    starts_at: datetime,
    teacher_name: str | None,
    room_name: str | None,
    forecast: WeatherForecast | None = None,
    checkin_hint: bool = True,
) -> str:
    """Build a rich reminder: weather, room, teacher, mat, water, check-in."""
    lines = [f"Erinnerung: {course_name} am {starts_at.strftime('%d.%m. um %H:%M')} Uhr."]
    if teacher_name:
        lines.append(f"Lehrer: {teacher_name}.")
    if room_name:
        lines.append(f"Raum: {room_name}.")
    lines.append("Bitte Matte und Trinkflasche mitbringen.")
    if forecast is not None:
        advice = weather_advice(forecast)
        if advice:
            lines.append(advice)
    if checkin_hint:
        lines.append("Check-in per QR-Code am Studioeingang.")
    return " ".join(lines)


async def schedule_session_reminders(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    *,
    channel: NotificationChannel = NotificationChannel.PUSH,
    forecast: WeatherForecast | None = None,
    reminder_at: datetime | None = None,
) -> list[Notification]:
    """Create a smart reminder for every booked member of a session."""
    from app.models.booking import Booking, BookingStatus

    bookings = (
        await db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.session_id == session.id,
                Booking.status == BookingStatus.BOOKED,
            )
        )
    ).scalars().all()

    course_name = getattr(session.course, "name", "Kurs")
    room_name = getattr(getattr(session, "room", None), "name", None)

    created: list[Notification] = []
    for b in bookings:
        member = (
            await db.execute(select(Member).where(Member.id == b.member_id))
        ).scalar_one_or_none()
        body = compose_smart_reminder(
            course_name=course_name,
            starts_at=session.starts_at,
            teacher_name=None,
            room_name=room_name,
            forecast=forecast,
        )
        n = await enqueue(
            db,
            tenant_id,
            channel=channel,
            body=body,
            member_id=member.id if member else None,
            subject=f"Erinnerung: {course_name}",
            scheduled_for=reminder_at,
            template="smart_reminder",
        )
        created.append(n)
    return created


async def notify_session_cancelled(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    session: CourseSession,
    *,
    reason: str | None = None,
    channel: NotificationChannel = NotificationChannel.PUSH,
) -> list[Notification]:
    """Notify every booked member that a session has been cancelled."""
    from app.models.booking import Booking, BookingStatus

    bookings = (
        (
            await db.execute(
                select(Booking).where(
                    Booking.tenant_id == tenant_id,
                    Booking.session_id == session.id,
                    Booking.status == BookingStatus.BOOKED,
                )
            )
        )
        .scalars()
        .all()
    )

    course_name = getattr(session.course, "name", "Kurs")
    when = session.starts_at.strftime("%d.%m. um %H:%M")
    body = f"Abgesagt: {course_name} am {when} Uhr entfällt leider."
    if reason:
        body += f" Grund: {reason}"

    created: list[Notification] = []
    for b in bookings:
        n = await enqueue(
            db,
            tenant_id,
            channel=channel,
            body=body,
            member_id=b.member_id,
            subject=f"Abgesagt: {course_name}",
            template="session_cancelled",
        )
        created.append(n)
    return created
