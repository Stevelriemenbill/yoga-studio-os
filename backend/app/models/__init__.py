from app.models.automation import AutomationRule, AutomationTrigger
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.checkin import (
    Attendance,
    AttendanceStatus,
    CheckIn,
    CheckInMethod,
)
from app.models.course import Course, CourseLevel, Room
from app.models.event import (
    Event,
    EventRegistration,
    EventRegistrationStatus,
    EventType,
)
from app.models.insight import AIInsight, InsightType
from app.models.member import Member, MembershipType
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.models.session import CourseSession, SessionStatus
from app.models.tenant import Tenant
from app.models.training import (
    TrainingArea,
    TrainingHours,
    TrainingRequirement,
)
from app.models.user import STAFF_ROLES, User, UserRole
from app.models.waitlist import WaitlistEntry, WaitlistStatus

__all__ = [
    "Tenant",
    "User",
    "UserRole",
    "STAFF_ROLES",
    "Room",
    "Course",
    "CourseLevel",
    "CourseSession",
    "SessionStatus",
    "Member",
    "MembershipType",
    "Booking",
    "BookingStatus",
    "BookingSource",
    "WaitlistEntry",
    "WaitlistStatus",
    "CheckIn",
    "CheckInMethod",
    "Attendance",
    "AttendanceStatus",
    "TrainingHours",
    "TrainingRequirement",
    "TrainingArea",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "AutomationRule",
    "AutomationTrigger",
    "AIInsight",
    "InsightType",
    "Event",
    "EventRegistration",
    "EventType",
    "EventRegistrationStatus",
]
