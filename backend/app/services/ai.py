"""Fürsorge- und Begleitungs-Werkzeuge.

Diese Werkzeuge unterstützen Lehrende dabei, ihre Schüler:innen zu begleiten und
die Lehrer-Schüler-Beziehung zu stärken – nicht dabei, das Studio zu vergrößern.
Der Fokus liegt auf Menschen, nicht auf Auslastung: Wer war länger nicht da und
könnte sich über eine persönliche Nachricht freuen? Wie sieht die Praxis-Reise
einer Person aus? Wann steht ein Meilenstein an, den man gemeinsam feiern kann?
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.booking import Booking, BookingStatus
from app.models.checkin import CheckIn
from app.models.course import Course
from app.models.insight import AIInsight, InsightType
from app.models.member import Member
from app.models.session import CourseSession

# Praxis-Meilensteine, die es wert sind, gemeinsam gewürdigt zu werden.
PRACTICE_MILESTONES = [1, 10, 25, 50, 100, 200, 365]


class InsightRepository(TenantRepository[AIInsight]):
    model = AIInsight


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def _attended_sessions(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> list[tuple[datetime, uuid.UUID]]:
    """(starts_at, course_id) jeder besuchten Session, aufsteigend nach Datum.

    Als 'besucht' zählt eine Buchung mit Status ATTENDED oder ein Check-in.
    """
    rows = (
        await db.execute(
            select(CourseSession.starts_at, CourseSession.course_id)
            .join(Booking, Booking.session_id == CourseSession.id)
            .where(
                Booking.tenant_id == tenant_id,
                Booking.member_id == member_id,
                Booking.status == BookingStatus.ATTENDED,
            )
        )
    ).all()
    checkins = (
        await db.execute(
            select(CourseSession.starts_at, CourseSession.course_id)
            .join(CheckIn, CheckIn.session_id == CourseSession.id)
            .where(
                CheckIn.tenant_id == tenant_id,
                CheckIn.member_id == member_id,
            )
        )
    ).all()
    seen: dict[datetime, uuid.UUID] = {}
    for starts_at, course_id in [*rows, *checkins]:
        seen[_aware(starts_at)] = course_id
    return sorted(seen.items())


async def students_needing_care(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    quiet_days: int = 21,
    lookback_days: int = 120,
) -> list[dict]:
    """Schüler:innen, die zuvor regelmäßig kamen und zuletzt fehlten.

    Kein Marketing-Trigger: eine sanfte Erinnerung, sich persönlich zu melden
    ('Wie geht es dir?'). Sortiert danach, wer am längsten fehlt.
    """
    now = datetime.now(UTC)
    lookback = now - timedelta(days=lookback_days)

    members = (
        await db.execute(
            select(Member).where(Member.tenant_id == tenant_id)
        )
    ).scalars().all()

    result: list[dict] = []
    for m in members:
        history = await _attended_sessions(db, tenant_id, m.id)
        recent = [d for d, _ in history if d >= lookback]
        if len(recent) < 3:
            # Zu wenig gemeinsame Geschichte, um Rhythmus zu erkennen.
            continue
        last_visit = max(recent)
        days_since = (now - last_visit).days
        if days_since < quiet_days:
            continue
        # Wie regelmäßig war die Person vorher da (Besuche pro Woche)?
        span_days = max((last_visit - min(recent)).days, 1)
        per_week = len(recent) / (span_days / 7)
        result.append(
            {
                "member_id": str(m.id),
                "name": m.full_name,
                "days_since_last_visit": days_since,
                "last_visit": last_visit.date().isoformat(),
                "usual_visits_per_week": round(per_week, 1),
                "total_visits": len(history),
            }
        )
    result.sort(key=lambda x: -x["days_since_last_visit"])
    return result


async def student_journey(
    db: AsyncSession, tenant_id: uuid.UUID, member_id: uuid.UUID
) -> dict:
    """Die Praxis-Reise einer Person: Konstanz, Vielfalt, Meilensteine."""
    member = (
        await db.execute(
            select(Member).where(
                Member.tenant_id == tenant_id, Member.id == member_id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        return {}

    history = await _attended_sessions(db, tenant_id, member_id)
    total = len(history)
    now = datetime.now(UTC)

    # Kursarten-Vielfalt.
    course_counts: dict[uuid.UUID, int] = defaultdict(int)
    for _, course_id in history:
        course_counts[course_id] += 1
    course_names: dict[uuid.UUID, str] = {}
    if course_counts:
        rows = (
            await db.execute(
                select(Course.id, Course.name).where(
                    Course.tenant_id == tenant_id,
                    Course.id.in_(list(course_counts.keys())),
                )
            )
        ).all()
        course_names = {cid: name for cid, name in rows}
    practiced_styles = [
        {"course": course_names.get(cid, "—"), "visits": cnt}
        for cid, cnt in sorted(course_counts.items(), key=lambda x: -x[1])
    ]

    # Konstanz der letzten 8 Wochen.
    eight_weeks_ago = now - timedelta(weeks=8)
    recent = [d for d, _ in history if d >= eight_weeks_ago]
    weeks_practiced = len({(d.isocalendar().year, d.isocalendar().week) for d in recent})
    last_visit = max((d for d, _ in history), default=None)
    days_since = (now - last_visit).days if last_visit else None

    # Erreichte Meilensteine und der nächste.
    reached = [m for m in PRACTICE_MILESTONES if total >= m]
    next_milestone = next((m for m in PRACTICE_MILESTONES if m > total), None)

    member_since = _aware(member.created_at)
    days_member = (now - member_since).days

    return {
        "member_id": str(member.id),
        "name": member.full_name,
        "member_since": member_since.date().isoformat(),
        "days_as_member": days_member,
        "total_practices": total,
        "practiced_styles": practiced_styles,
        "weeks_practiced_recent": weeks_practiced,
        "last_visit": last_visit.date().isoformat() if last_visit else None,
        "days_since_last_visit": days_since,
        "milestones_reached": reached,
        "next_milestone": next_milestone,
        "practices_to_next_milestone": (
            next_milestone - total if next_milestone else None
        ),
    }


async def care_insights(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[AIInsight]:
    """Fürsorgliche Hinweise für Lehrende erzeugen und speichern.

    - Wer war länger nicht da und könnte sich über eine Nachricht freuen?
    - Wer steht kurz vor einem Praxis-Meilenstein zum gemeinsamen Feiern?
    """
    repo = InsightRepository(db, tenant_id)
    created: list[AIInsight] = []

    care = await students_needing_care(db, tenant_id)
    for c in care[:5]:
        created.append(
            repo.add(
                AIInsight(
                    type=InsightType.CARE,
                    title=f"{c['name']} war eine Weile nicht da",
                    body=(
                        f"{c['name']} praktizierte sonst etwa "
                        f"{c['usual_visits_per_week']}× pro Woche, war aber seit "
                        f"{c['days_since_last_visit']} Tagen nicht mehr da. "
                        "Vielleicht magst du dich kurz melden und fragen, wie es geht."
                    ),
                    data=c,
                )
            )
        )

    # Bevorstehende Meilensteine unter allen Mitgliedern.
    members = (
        await db.execute(select(Member).where(Member.tenant_id == tenant_id))
    ).scalars().all()
    for m in members:
        history = await _attended_sessions(db, tenant_id, m.id)
        total = len(history)
        upcoming = next(
            (ms for ms in PRACTICE_MILESTONES if 0 < ms - total <= 2), None
        )
        if upcoming is not None:
            created.append(
                repo.add(
                    AIInsight(
                        type=InsightType.MILESTONE,
                        title=f"{m.full_name} nähert sich der {upcoming}. Praxis",
                        body=(
                            f"{m.full_name} steht kurz vor der {upcoming}. Praxis "
                            f"({total} bisher). Ein schöner Moment, das gemeinsam "
                            "zu würdigen."
                        ),
                        data={"member_id": str(m.id), "milestone": upcoming},
                    )
                )
            )

    await db.commit()
    for i in created:
        await db.refresh(i)
    return created


async def assistant_answer(
    db: AsyncSession, tenant_id: uuid.UUID, question: str
) -> AIInsight:
    """Beantwortet Lehrer-Fragen rund um die Begleitung der Schüler:innen.

    Regelbasiertes Intent-Matching über die eigenen Studiodaten – bewusst
    beziehungsorientiert statt umsatz-/auslastungsorientiert. Ein LLM kann
    später auf denselben berechneten Kontext aufgesetzt werden.
    """
    q = question.lower()

    care_keywords = (
        "aufmerksam", "vermiss", "lange nicht", "melden", "fürsorge", "fuersorge"
    )
    if any(k in q for k in care_keywords):
        care = await students_needing_care(db, tenant_id)
        if care:
            names = ", ".join(c["name"] for c in care[:5])
            body = (
                f"Diese Schüler:innen waren länger nicht da und könnten sich über "
                f"ein Lebenszeichen freuen: {names}. "
                f"Am längsten fehlt {care[0]['name']} "
                f"({care[0]['days_since_last_visit']} Tage)."
            )
        else:
            body = (
                "Aktuell fehlt niemand aus dem gewohnten Rhythmus – "
                "eure Gemeinschaft praktiziert beständig."
            )
    elif any(k in q for k in ("meilenstein", "jubiläum", "jubilaeum", "feiern")):
        insights = await care_insights(db, tenant_id)
        milestones = [i for i in insights if i.type == InsightType.MILESTONE]
        if milestones:
            body = "Bald zu feiern: " + " ".join(i.title + "." for i in milestones[:5])
        else:
            body = "Zurzeit stehen keine unmittelbaren Meilensteine an."
    elif any(k in q for k in ("neu", "willkommen", "anfänger", "anfaenger")):
        now = datetime.now(UTC)
        recent = now - timedelta(days=30)
        count = (
            await db.execute(
                select(func.count())
                .select_from(Member)
                .where(
                    Member.tenant_id == tenant_id,
                    Member.created_at >= recent,
                )
            )
        ).scalar_one()
        body = (
            f"In den letzten 30 Tagen sind {count} neue Menschen dazugekommen. "
            "Ein herzliches Willkommen und etwas Extra-Aufmerksamkeit helfen ihnen "
            "beim Ankommen."
        )
    else:
        care = await students_needing_care(db, tenant_id)
        body = (
            "Frag mich, wer gerade Aufmerksamkeit gebrauchen könnte, wer bald einen "
            "Meilenstein feiert oder wer neu dazugekommen ist. "
            f"Zurzeit könnten sich {len(care)} Schüler:innen über eine Nachricht freuen."
        )

    repo = InsightRepository(db, tenant_id)
    insight = repo.add(
        AIInsight(
            type=InsightType.ASSISTANT_ANSWER,
            title=question[:255],
            body=body,
        )
    )
    await db.commit()
    await db.refresh(insight)
    return insight
