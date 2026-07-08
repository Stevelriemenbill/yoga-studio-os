import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TokenType = Literal["access", "refresh", "invite", "staff_invite"]

# bcrypt operates on the first 72 bytes only; enforce explicitly.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str,
    tenant_id: str,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "tid": tenant_id,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str, tenant_id: str, role: str) -> str:
    return _create_token(
        subject,
        tenant_id,
        role,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str, tenant_id: str, role: str) -> str:
    return _create_token(
        subject,
        tenant_id,
        role,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_invite_token(member_id: str, tenant_id: str) -> str:
    """Token embedded in a member invitation link. Subject is the member id."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": member_id,
        "tid": tenant_id,
        "type": "invite",
        "iat": now,
        "exp": now + timedelta(days=settings.INVITE_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_staff_invite_token(invite_id: str, tenant_id: str, role: str) -> str:
    """Token embedded in a staff invitation link. Subject is the invite id."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": invite_id,
        "tid": tenant_id,
        "role": role,
        "type": "staff_invite",
        "iat": now,
        "exp": now + timedelta(days=settings.INVITE_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if expected_type is not None and payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type: expected {expected_type}")
    return payload
