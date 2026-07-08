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
    body = resp.json()
    assert body["email"] == "admin@zenflow.example.com"
    # Studio context for the app shell.
    assert body["studio_name"] == "Zen Flow Studio"
    assert body["theme_preset"] == "emerald"
    assert body["theme_mode"] == "light"


@pytest.mark.asyncio
async def test_get_theme_defaults(client):
    reg = (await _register(client)).json()
    token = reg["token"]["access_token"]
    resp = await client.get(
        "/api/v1/auth/theme", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"theme_preset": "emerald", "theme_mode": "light"}


@pytest.mark.asyncio
async def test_admin_updates_theme(client):
    reg = (await _register(client)).json()
    token = reg["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/api/v1/auth/theme",
        json={"theme_preset": "violet", "theme_mode": "dark"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"theme_preset": "violet", "theme_mode": "dark"}
    # Persisted and reflected in /me.
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    assert me["theme_preset"] == "violet"
    assert me["theme_mode"] == "dark"


@pytest.mark.asyncio
async def test_update_theme_rejects_unknown_preset(client):
    reg = (await _register(client)).json()
    token = reg["token"]["access_token"]
    resp = await client.patch(
        "/api/v1/auth/theme",
        json={"theme_preset": "chartreuse"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_member_cannot_update_theme(client):
    staff = {"Authorization": f"Bearer {(await _register(client)).json()['token']['access_token']}"}
    member = (
        await client.post(
            "/api/v1/members",
            json={"first_name": "Mira", "last_name": "M", "email": "mira@example.com"},
            headers=staff,
        )
    ).json()
    token = (
        await client.post(
            f"/api/v1/members/{member['id']}/invite", headers=staff
        )
    ).json()["token"]
    accepted = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    member_token = accepted.json()["token"]["access_token"]
    # Members may read the theme but not change it.
    read = await client.get(
        "/api/v1/auth/theme",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert read.status_code == 200
    resp = await client.patch(
        "/api/v1/auth/theme",
        json={"theme_preset": "violet"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert resp.status_code == 403


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
