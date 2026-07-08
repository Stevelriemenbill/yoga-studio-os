import uuid
from pathlib import Path

from app.core.config import settings


def _course_dir(tenant_id: uuid.UUID, course_id: uuid.UUID) -> Path:
    """Directory (relative structure) where a course's files are stored."""
    return Path(settings.MEDIA_ROOT) / "courses" / str(tenant_id) / str(course_id)


def save_course_file(
    tenant_id: uuid.UUID,
    course_id: uuid.UUID,
    original_filename: str,
    content: bytes,
) -> tuple[str, str]:
    """Persist an uploaded file to the media volume.

    Returns ``(stored_name, relative_url)`` where ``relative_url`` is a path
    below ``MEDIA_URL`` suitable for serving via StaticFiles.
    """
    suffix = Path(original_filename).suffix
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    directory = _course_dir(tenant_id, course_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / stored_name).write_bytes(content)
    rel = f"courses/{tenant_id}/{course_id}/{stored_name}"
    return stored_name, rel


def course_file_url(
    tenant_id: uuid.UUID, course_id: uuid.UUID, stored_name: str
) -> str:
    """Public URL (under MEDIA_URL) for a stored course file."""
    return f"{settings.MEDIA_URL}/courses/{tenant_id}/{course_id}/{stored_name}"


def delete_course_file(
    tenant_id: uuid.UUID, course_id: uuid.UUID, stored_name: str
) -> None:
    path = _course_dir(tenant_id, course_id) / stored_name
    path.unlink(missing_ok=True)
