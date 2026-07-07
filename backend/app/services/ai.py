import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import TenantRepository
from app.models.booking import Booking, BookingStatus
from app.models.insight import AIInsight, InsightType
from app.models.session import CourseSession, SessionStatus
from app.services import analytics as analytics_service


class InsightRepository(TenantRepository[AIInsight]):
    model = AIInsight


async def _historical_fill_rate(
    db: AsyncSession, tenant_id: uuid.UUID, course_id: uuid.UUID
) -> float:
    """Average utilization of past sessions of a course."""
    sessions = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.course_id == course_id,
                CourseSession.starts_at < datetime.now(),
            )
        )
    ).scalars().all()
    if not sessions:
        return 0.0
    total_util = 0.0
    counted = 0
    for s in sessions:
        booked = (
            await db.execute(
                select(func.count())
                .select_from(Booking)
                .where(
                    Booking.tenant_id == tenant_id,
                    Booking.session_id == s.id,
                    Booking.status.in_(
                        [BookingStatus.BOOKED, BookingStatus.ATTENDED]
                    ),
                )
            )
        ).scalar_one()
        if s.effective_capacity:
            total_util += booked / s.effective_capacity
            counted += 1
    return total_util / counted if counted else 0.0


async def forecast_fill(
    db: AsyncSession, tenant_id: uuid.UUID, days_ahead: int = 14
) -> list[dict]:
    """Predict which upcoming sessions are likely to fill up.

    Uses the course's historical fill rate as a simple predictor.
    """
    now = datetime.now()
    horizon = now + timedelta(days=days_ahead)
    upcoming = (
        await db.execute(
            select(CourseSession).where(
                CourseSession.tenant_id == tenant_id,
                CourseSession.status == SessionStatus.SCHEDULED,
                CourseSession.starts_at >= now,
                CourseSession.starts_at <= horizon,
            )
        )
    ).scalars().all()

    predictions = []
    fill_cache: dict[uuid.UUID, float] = {}
    for s in upcoming:
        if s.course_id not in fill_cache:
            fill_cache[s.course_id] = await _historical_fill_rate(
                db, tenant_id, s.course_id
            )
        predicted = fill_cache[s.course_id]
        predictions.append(
            {
                "session_id": str(s.id),
                "course_id": str(s.course_id),
                "starts_at": s.starts_at.isoformat(),
                "predicted_fill_rate": round(predicted, 3),
                "likely_full": predicted >= 0.9,
                "likely_underbooked": predicted < 0.4,
            }
        )
    predictions.sort(key=lambda x: -x["predicted_fill_rate"])
    return predictions


async def generate_insights(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[AIInsight]:
    """Produce recommendation/anomaly insights and persist them."""
    end = datetime.now()
    start = end - timedelta(days=30)
    kpis = await analytics_service.studio_kpis(db, tenant_id, start, end)
    heat = await analytics_service.heatmap(db, tenant_id, start, end)

    repo = InsightRepository(db, tenant_id)
    created: list[AIInsight] = []

    if kpis["no_show_rate"] > 0.15:
        created.append(
            repo.add(
                AIInsight(
                    type=InsightType.ANOMALY,
                    title="Hohe No-Show-Rate",
                    body=(
                        f"Die No-Show-Rate liegt bei {kpis['no_show_rate']:.0%}. "
                        "Erwäge Erinnerungen 2h vorher oder ein Überbuchungsmodell."
                    ),
                    confidence=0.8,
                    data={"no_show_rate": kpis["no_show_rate"]},
                )
            )
        )

    hot = [c for c in heat if c["level"] == "red"]
    for c in hot[:3]:
        weekday_names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        created.append(
            repo.add(
                AIInsight(
                    type=InsightType.RECOMMENDATION,
                    title="Regelmäßig ausgebucht",
                    body=(
                        f"{weekday_names[c['weekday']]} {c['hour']}:00 Uhr ist regelmäßig "
                        f"überbucht ({c['utilization']:.0%}). Zusätzlichen Slot anbieten?"
                    ),
                    confidence=0.7,
                    data=c,
                )
            )
        )

    if kpis["utilization"] < 0.4 and kpis["sessions"] > 0:
        created.append(
            repo.add(
                AIInsight(
                    type=InsightType.RECOMMENDATION,
                    title="Niedrige Auslastung",
                    body=(
                        f"Die Auslastung liegt bei {kpis['utilization']:.0%}. "
                        "Prüfe Kurszeiten, Marketing oder Reaktivierungskampagnen."
                    ),
                    confidence=0.6,
                    data={"utilization": kpis["utilization"]},
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
    """Answer a natural-language operator question using studio data.

    Rule-based intent matching over the studio's own analytics. This keeps the
    assistant fully functional without an external LLM; an LLM can be layered
    on top by feeding it the same computed context.
    """
    q = question.lower()
    end = datetime.now()
    start = end - timedelta(days=30)
    kpis = await analytics_service.studio_kpis(db, tenant_id, start, end)

    if any(k in q for k in ("auslastung", "utilization", "voll")):
        teachers = await analytics_service.teacher_analytics(db, tenant_id, start, end)
        top = teachers[0] if teachers else None
        body = (
            f"Aktuelle Auslastung: {kpis['utilization']:.0%} über {kpis['sessions']} "
            f"Kurse. No-Show-Rate {kpis['no_show_rate']:.0%}."
        )
        if top:
            body += f" Bester Lehrer: {top['teacher_id']} mit {top['utilization']:.0%} Auslastung."
    elif any(k in q for k in ("lehrer", "teacher", "wiederkehr")):
        teachers = await analytics_service.teacher_analytics(db, tenant_id, start, end)
        if teachers:
            best = max(teachers, key=lambda t: t["unique_members"])
            body = (
                f"Lehrer {best['teacher_id']} hat mit {best['unique_members']} "
                "wiederkehrenden Teilnehmern die höchste Bindung."
            )
        else:
            body = "Noch keine Lehrer-Daten verfügbar."
    elif any(k in q for k in ("kontaktieren", "reaktiv", "inaktiv")):
        body = (
            "Kontaktiere Mitglieder ohne Buchung in den letzten 30 Tagen. "
            "Richte dafür eine Automatisierungsregel (INACTIVE_DAYS) ein."
        )
    elif any(k in q for k in ("montag", "kurse anbieten", "welche kurse")):
        popular = await analytics_service.popular_courses(db, tenant_id, start, end)
        if popular:
            body = (
                f"Beliebtester Kurs: {popular[0]['course_id']} "
                f"({popular[0]['bookings']} Buchungen). Erwäge zusätzliche Slots."
            )
        else:
            body = "Noch nicht genug Buchungsdaten für eine Empfehlung."
    else:
        body = (
            f"Übersicht: {kpis['sessions']} Kurse, Auslastung {kpis['utilization']:.0%}, "
            f"No-Shows {kpis['no_show_rate']:.0%}, {kpis['new_members']} neue Mitglieder."
        )

    repo = InsightRepository(db, tenant_id)
    insight = repo.add(
        AIInsight(
            type=InsightType.ASSISTANT_ANSWER,
            title=question[:255],
            body=body,
            data={"kpis": kpis},
        )
    )
    await db.commit()
    await db.refresh(insight)
    return insight
