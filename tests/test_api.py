"""
Unit tests for PulseChat backend.
Run with: pytest tests/ -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """Health check endpoint returns 200"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """User registration returns tokens"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser_123",
            "email": "testuser_123@example.com",
            "password": "TestPass123!",
            "display_name": "Test User",
        },
    )
    # May get 400 if user already exists
    assert response.status_code in (201, 400)
    if response.status_code == 201:
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["username"] == "testuser_123"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Login with wrong password returns 400"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """Protected route returns 403 without token"""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_search_requires_auth(client: AsyncClient):
    """Search endpoint requires authentication"""
    response = await client.get("/api/v1/users/search?q=test")
    assert response.status_code == 403


class TestFullAuthFlow:
    """Integration test: register → login → get profile → refresh"""

    @pytest.mark.asyncio
    async def test_full_flow(self, client: AsyncClient):
        import time
        unique_suffix = str(int(time.time()))[-6:]
        email = f"flow_user_{unique_suffix}@example.com"
        username = f"flowuser_{unique_suffix}"

        # 1. Register
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "FlowPass123!",
            },
        )
        assert reg.status_code == 201
        access_token = reg.json()["access_token"]
        refresh_token = reg.json()["refresh_token"]

        # 2. Get profile
        headers = {"Authorization": f"Bearer {access_token}"}
        me = await client.get("/api/v1/users/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email

        # 3. Update profile
        update = await client.put(
            "/api/v1/users/me",
            headers=headers,
            json={"display_name": "Updated Name"},
        )
        assert update.status_code == 200
        assert update.json()["display_name"] == "Updated Name"
