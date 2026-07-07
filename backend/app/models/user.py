import enum

from sqlalchemy import Boolean, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.mixins import TenantMixin


class UserRole(str, enum.Enum):
    """Roles within a studio. Ordered roughly by privilege."""

    STUDIO_ADMIN = "studio_admin"
    STUDIO_MANAGER = "studio_manager"
    TEACHER = "teacher"
    RECEPTION = "reception"
    MEMBER = "member"
    TRAINEE = "trainee"  # Yogalehrer in Ausbildung


# Roles allowed to manage the studio (admin panel access)
STAFF_ROLES = {
    UserRole.STUDIO_ADMIN,
    UserRole.STUDIO_MANAGER,
    UserRole.RECEPTION,
    UserRole.TEACHER,
}


class User(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        # Email is unique per tenant, not globally
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=32),
        default=UserRole.MEMBER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role.value})>"
