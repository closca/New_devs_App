from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from app.services.cache import get_revenue_summary
from app.services.reservations import DatabaseUnavailableError, PropertyNotFoundError
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    year: int = Query(..., ge=2000, le=2100, description="Calendar year of the reporting month"),
    month: int = Query(..., ge=1, le=12, description="Reporting month, 1-12"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:

    tenant_id = getattr(current_user, "tenant_id", "default_tenant") or "default_tenant"

    try:
        revenue_data = await get_revenue_summary(property_id, tenant_id, year, month)
    except PropertyNotFoundError:
        raise HTTPException(status_code=404, detail="Property not found")
    except DatabaseUnavailableError:
        raise HTTPException(status_code=503, detail="Revenue data temporarily unavailable")

    total_revenue_float = float(revenue_data['total'])

    return {
        "property_id": revenue_data['property_id'],
        "year": revenue_data['year'],
        "month": revenue_data['month'],
        "total_revenue": total_revenue_float,
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }
