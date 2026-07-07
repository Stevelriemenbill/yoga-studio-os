import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import GUID


class TenantMixin:
    """Adds a tenant_id foreign key to a model for multi-tenant scoping.

    Every tenant-scoped table must inherit this. Queries MUST always
    filter by tenant_id (enforced via the tenant-aware repository/deps).
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def tenant_index(table_name: str, *columns: str) -> Index:
    """Helper to build a composite index prefixed by tenant_id."""
    return Index(
        f"ix_{table_name}_tenant_{'_'.join(columns)}",
        "tenant_id",
        *columns,
    )
