import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.auth import authenticate_request
from app.models.auth import AuthenticatedUser
from app.models.property import PropertyListResponse
from app.services.properties import list_properties_for_tenant
from app.services.reservations import DatabaseUnavailableError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
async def list_properties(
    response: Response,
    user: AuthenticatedUser = Depends(authenticate_request),
) -> PropertyListResponse:
    """
    List the properties that belong to the authenticated user's tenant.

    Fails closed: a user without a tenant gets 403 rather than a default tenant's data.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant associated with this account",
        )

    try:
        items = await list_properties_for_tenant(user.tenant_id)
    except DatabaseUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Property data temporarily unavailable",
        )

    # Tenant data must never be stored by a shared cache.
    response.headers["Cache-Control"] = "private, no-store"

    return PropertyListResponse(items=items, total=len(items))
