from fastapi import APIRouter

from app.api.v1 import (
    auth,
    bookings,
    checkin,
    courses,
    members,
    training,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(members.router)
api_router.include_router(courses.router)
api_router.include_router(courses.rooms_router)
api_router.include_router(courses.sessions_router)
api_router.include_router(bookings.router)
api_router.include_router(bookings.waitlist_router)
api_router.include_router(checkin.router)
api_router.include_router(checkin.attendance_router)
api_router.include_router(training.router)
