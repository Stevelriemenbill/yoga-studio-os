import pytest

REGISTER_PAYLOAD = {
    "studio_name": "Zen Flow Studio",
    "studio_slug": "zen-flow",
    "admin_email": "admin@zenflow.example.com",
    "admin_password": "supersecret1",
    "admin_full_name": "Alex Admin",
}


async def _register(client, **overrides):
    payload = {**REGISTER_PAYLOAD, **overrides}
    return await client.post("/api/v1/auth/register", json=payload)


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_studio_creates_tenant_and_admin(client):
    resp = await _register(client)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["tenant"]["slug"] == "zen-flow"
    assert data["user"]["role"] == "studio_admin"
    assert data["user"]["email"] == "admin@zenflow.example.com"
    assert data["token"]["access_token"]
    assert data["token"]["refresh_token"]


@pytest.mark.asyncio
async def test_register_duplicate_slug_conflicts(client):
    await _register(client)
    resp = await _register(client, admin_email="other@zenflow.example.com")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_slug(client):
    resp = await _register(client, studio_slug="Not Valid Slug!")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@zenflow.example.com",
            "password": "supersecret1",
            "tenant_slug": "zen-flow",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@zenflow.example.com",
            "password": "wrongpass1",
            "tenant_slug": "zen-flow",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_tenant(client):
    await _register(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@zenflow.example.com",
            "password": "supersecret1",
            "tenant_slug": "does-not-exist",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client):
    reg = (await _register(client)).json()
    token = reg["token"]["access_token"]
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@zenflow.example.com"


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client):
    reg = (await _register(client)).json()
    refresh_token = reg["token"]["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client):
    reg = (await _register(client)).json()
    access_token = reg["token"]["access_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_same_email_different_tenants_allowed(client):
    await _register(client)
    resp = await _register(
        client, studio_slug="other-studio", studio_name="Other Studio"
    )
    assert resp.status_code == 201
