from typing import List

from pydantic import BaseModel


class PropertyOut(BaseModel):
    """A property as exposed to the tenant that owns it."""

    id: str
    name: str
    timezone: str


class PropertyListResponse(BaseModel):
    """List envelope; leaves room for pagination without a breaking change."""

    items: List[PropertyOut]
    total: int
