import json
import redis.asyncio as redis
from typing import Dict, Any
import os

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

REVENUE_CACHE_TTL_SECONDS = 300


def revenue_cache_key(tenant_id: str, property_id: str, year: int, month: int) -> str:
    """
    Cache key for a monthly revenue figure.

    Property ids are only unique per tenant (properties has a composite PK), and the
    figure depends on the period, so both must be part of the key.
    """
    return f"revenue:{tenant_id}:{property_id}:{year:04d}-{month:02d}"


async def get_revenue_summary(
    property_id: str, tenant_id: str, year: int, month: int
) -> Dict[str, Any]:
    """
    Fetches the monthly revenue summary, utilizing caching to improve performance.
    """
    cache_key = revenue_cache_key(tenant_id, property_id, year, month)

    # Try to get from cache
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Revenue calculation is delegated to the reservation service.
    from app.services.reservations import calculate_monthly_revenue

    # Calculate revenue (errors propagate and are never cached)
    result = await calculate_monthly_revenue(property_id, tenant_id, year, month)

    # Cache the result for 5 minutes
    await redis_client.setex(cache_key, REVENUE_CACHE_TTL_SECONDS, json.dumps(result))

    return result
