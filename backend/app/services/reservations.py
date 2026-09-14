from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Tuple

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


class DatabaseUnavailableError(RuntimeError):
    """Raised when the reservations database cannot be reached."""


class PropertyNotFoundError(ValueError):
    """Raised when a property does not exist for the given tenant."""


def month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    """
    Half-open [start, end) wall-clock bounds for a calendar month.

    These are deliberately naive datetimes: the SQL query compares them against
    `check_in_date AT TIME ZONE properties.timezone`, i.e. the check-in time as
    seen on the property's own clock, so the month boundary is local to the property.
    """
    if not 1 <= month <= 12:
        raise ValueError(f"month must be between 1 and 12, got {month}")

    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)
    return start_date, end_date


MONTHLY_REVENUE_SQL = text("""
    SELECT
        COALESCE(SUM(r.total_amount), 0) AS total_revenue,
        COUNT(r.id)                      AS reservation_count
    FROM properties p
    LEFT JOIN reservations r
        ON  r.property_id = p.id
        AND r.tenant_id   = p.tenant_id
        AND (r.check_in_date AT TIME ZONE p.timezone) >= :period_start
        AND (r.check_in_date AT TIME ZONE p.timezone) <  :period_end
    WHERE p.id = :property_id
      AND p.tenant_id = :tenant_id
    GROUP BY p.id, p.tenant_id
""")


async def calculate_monthly_revenue(
    property_id: str, tenant_id: str, year: int, month: int
) -> Dict[str, Any]:
    """
    Sum reservation revenue for one property, one tenant, one calendar month.

    A reservation belongs to the month in which it checks in, evaluated in the
    property's configured time zone (properties.timezone).
    """
    period_start, period_end = month_bounds(year, month)

    from app.core.database_pool import db_pool

    await db_pool.initialize()
    if not db_pool.session_factory:
        raise DatabaseUnavailableError("Database pool not available")

    try:
        async with db_pool.get_session() as session:
            result = await session.execute(MONTHLY_REVENUE_SQL, {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "period_start": period_start,
                "period_end": period_end,
            })
            row = result.fetchone()
    except (DBAPIError, OSError) as exc:
        # Engine creation is lazy, so connection failures (DNS, refused, timeouts)
        # surface here rather than in initialize(). Never fall back to fabricated data.
        raise DatabaseUnavailableError(f"Database unavailable: {exc.__class__.__name__}") from exc

    if row is None:
        # The LEFT JOIN guarantees a row whenever the property exists for this tenant.
        raise PropertyNotFoundError(f"Property {property_id} not found for tenant {tenant_id}")

    total_revenue = Decimal(str(row.total_revenue))

    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "year": year,
        "month": month,
        "total": str(total_revenue),
        "currency": "USD",
        "count": int(row.reservation_count),
    }
