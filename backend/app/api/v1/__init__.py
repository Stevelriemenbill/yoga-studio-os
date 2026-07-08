from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    auth,
    automations,
    bookings,
    checkin,
    courses,
    events,
    integrations,
    me,
    members,
    notifications,
    training,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(members.router)
api_router.include_router(me.router)
api_router.include_router(courses.router)
api_router.include_router(courses.rooms_router)
api_router.include_router(courses.sessions_router)
api_router.include_router(bookings.router)
api_router.include_router(bookings.waitlist_router)
api_router.include_router(checkin.router)
api_router.include_router(checkin.attendance_router)
api_router.include_router(training.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
api_router.include_router(automations.router)
api_router.include_router(ai.router)
api_router.include_router(events.router)
api_router.include_router(integrations.router)
