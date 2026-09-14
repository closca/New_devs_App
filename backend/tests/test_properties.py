"""
Tests for GET /api/v1/properties (tenant-scoped property list).

No database is required: the service function is monkeypatched and auth is
overridden, in the same style as tests/test_revenue.py.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import authenticate_request
from app.models.auth import AuthenticatedUser
from app.models.property import PropertyListResponse
from app.services.reservations import DatabaseUnavailableError

TENANT_B_PROPERTIES = [
    {"id": "prop-004", "name": "Lakeside Cottage", "timezone": "America/New_York"},
    {"id": "prop-001", "name": "Mountain Lodge Beta", "timezone": "America/New_York"},
    {"id": "prop-005", "name": "Urban Loft Modern", "timezone": "America/New_York"},
]


def _user(tenant_id):
    return AuthenticatedUser(
        id="user-ocean", email="ocean@propertyflow.com",
        permissions=[], cities=[], is_admin=False, tenant_id=tenant_id,
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login_as(tenant_id):
    async def fake_user():
        return _user(tenant_id)
    app.dependency_overrides[authenticate_request] = fake_user


def test_returns_only_the_callers_tenant_properties(client, monkeypatch):
    seen = []

    async def fake_list(tenant_id):
        seen.append(tenant_id)
        return TENANT_B_PROPERTIES

    monkeypatch.setattr("app.api.v1.properties.list_properties_for_tenant", fake_list)
    _login_as("tenant-b")

    resp = client.get("/api/v1/properties")

    assert resp.status_code == 200
    assert seen == ["tenant-b"]
    body = PropertyListResponse.model_validate(resp.json())
    assert body.total == len(body.items) == 3
    assert [p.id for p in body.items] == ["prop-004", "prop-001", "prop-005"]
    assert body.items[1].name == "Mountain Lodge Beta"


def test_user_without_tenant_is_rejected_and_service_not_called(client, monkeypatch):
    async def fake_list(tenant_id):
        raise AssertionError("service must not be called without a tenant")

    monkeypatch.setattr("app.api.v1.properties.list_properties_for_tenant", fake_list)
    _login_as(None)

    resp = client.get("/api/v1/properties")

    assert resp.status_code == 403


def test_database_unavailable_maps_to_503(client, monkeypatch):
    async def fake_list(tenant_id):
        raise DatabaseUnavailableError("down")

    monkeypatch.setattr("app.api.v1.properties.list_properties_for_tenant", fake_list)
    _login_as("tenant-b")

    resp = client.get("/api/v1/properties")

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Property data temporarily unavailable"


def test_unauthenticated_request_is_rejected(client):
    resp = client.get("/api/v1/properties")

    assert resp.status_code == 401


def test_response_is_not_cacheable_by_shared_caches(client, monkeypatch):
    async def fake_list(tenant_id):
        return TENANT_B_PROPERTIES

    monkeypatch.setattr("app.api.v1.properties.list_properties_for_tenant", fake_list)
    _login_as("tenant-b")

    resp = client.get("/api/v1/properties")

    assert resp.headers["cache-control"] == "private, no-store"
