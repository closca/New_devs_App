"""
Tenant-scoped property listing.

Property ids are only unique per tenant (`properties` has a composite primary key
`(id, tenant_id)`), so every query here is filtered by tenant. The result is
deliberately NOT cached: the lookup is a single index scan on the primary key, and a
cache keyed on anything less than the tenant is exactly the class of bug that leaked
revenue between clients.
"""
import logging
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.services.reservations import DatabaseUnavailableError

logger = logging.getLogger(__name__)

LIST_PROPERTIES_SQL = text("""
    SELECT id, name, timezone
    FROM properties
    WHERE tenant_id = :tenant_id
    ORDER BY name
""")


async def list_properties_for_tenant(tenant_id: str) -> List[Dict[str, Any]]:
    """Return the properties owned by `tenant_id`, ordered by name."""
    from app.core.database_pool import db_pool

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise DatabaseUnavailableError("Database pool not available")

    try:
        async with db_pool.get_session() as session:
            result = await session.execute(LIST_PROPERTIES_SQL, {"tenant_id": tenant_id})
            rows = result.fetchall()
    except (DBAPIError, OSError) as exc:
        # Engine creation is lazy, so connection failures surface here.
        raise DatabaseUnavailableError(f"Database unavailable: {exc.__class__.__name__}") from exc

    properties = [
        {"id": row.id, "name": row.name, "timezone": row.timezone}
        for row in rows
    ]
    logger.debug("Listed %d properties for tenant %s", len(properties), tenant_id)
    return properties
