"""
Unit tests for monthly revenue reporting (no database required).

The DB-backed behaviour (the Paris month-boundary reservation landing in March)
is exercised against the running docker-compose stack; see ASSIGNMENT notes.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.services.reservations import month_bounds
from app.services.cache import revenue_cache_key


# --- period bounds -----------------------------------------------------------

def test_march_bounds_are_half_open_month():
    start, end = month_bounds(2024, 3)
    assert start == datetime(2024, 3, 1)
    assert end == datetime(2024, 4, 1)


def test_december_rolls_into_next_year():
    start, end = month_bounds(2024, 12)
    assert start == datetime(2024, 12, 1)
    assert end == datetime(2025, 1, 1)


@pytest.mark.parametrize("month", [0, 13, -1])
def test_invalid_month_rejected(month):
    with pytest.raises(ValueError):
        month_bounds(2024, month)


def test_bounds_are_naive_wall_clock():
    # The SQL compares against `check_in_date AT TIME ZONE properties.timezone`,
    # which yields a naive local timestamp, so bounds must be naive too.
    start, end = month_bounds(2024, 3)
    assert start.tzinfo is None and end.tzinfo is None


# --- cache key ---------------------------------------------------------------

def test_cache_key_differs_per_tenant_for_same_property():
    # prop-001 exists under both tenants (composite PK), so tenant must be in the key
    assert revenue_cache_key("tenant-a", "prop-001", 2024, 3) != \
           revenue_cache_key("tenant-b", "prop-001", 2024, 3)


def test_cache_key_differs_per_period():
    assert revenue_cache_key("tenant-a", "prop-001", 2024, 3) != \
           revenue_cache_key("tenant-a", "prop-001", 2024, 2)
    assert revenue_cache_key("tenant-a", "prop-001", 2024, 3) != \
           revenue_cache_key("tenant-a", "prop-001", 2025, 3)


def test_cache_key_is_zero_padded_and_readable():
    assert revenue_cache_key("tenant-a", "prop-001", 2024, 3) == "revenue:tenant-a:prop-001:2024-03"


# --- endpoint validation -----------------------------------------------------

@pytest.fixture
def client():
    from app.main import app
    from app.core.auth import authenticate_request
    from app.models.auth import AuthenticatedUser

    async def fake_user():
        return AuthenticatedUser(
            id="user-sunset", email="sunset@propertyflow.com",
            permissions=[], cities=[], is_admin=False, tenant_id="tenant-a",
        )

    app.dependency_overrides[authenticate_request] = fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_endpoint_rejects_month_13(client):
    r = client.get("/api/v1/dashboard/summary", params={"property_id": "prop-001", "year": 2024, "month": 13})
    assert r.status_code == 422


def test_endpoint_requires_period(client):
    r = client.get("/api/v1/dashboard/summary", params={"property_id": "prop-001"})
    assert r.status_code == 422
