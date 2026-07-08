import pytest

REGISTER_PAYLOAD = {
    "studio_name": "Zen Flow Studio",
    "studio_slug": "zen-flow",
    "admin_email": "admin@zenflow.example.com",
    "admin_password": "supersecret1",
    "admin_full_name": "Alex Admin",
}


async def _register(client):
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _auth_headers(client):
    reg = await _register(client)
    return {"Authorization": f"Bearer {reg['token']['access_token']}"}


async def _create_member(client, headers, **overrides):
    payload = {
        "first_name": "Mira",
        "last_name": "Member",
        "email": "mira@example.com",
        **overrides,
    }
    resp = await client.post("/api/v1/members", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_invite_member_returns_link(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers)
    resp = await client.post(
        f"/api/v1/members/{member['id']}/invite", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["token"]
    assert "/invite/" in data["invite_url"]


@pytest.mark.asyncio
async def test_invite_member_without_email_fails(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers, email=None)
    resp = await client.post(
        f"/api/v1/members/{member['id']}/invite", headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_preview_invite_returns_member_details(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers)
    token = (
        await client.post(f"/api/v1/members/{member['id']}/invite", headers=headers)
    ).json()["token"]

    resp = await client.get(f"/api/v1/auth/invite/{token}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == "mira@example.com"
    assert data["first_name"] == "Mira"
    assert data["studio_name"] == "Zen Flow Studio"


@pytest.mark.asyncio
async def test_preview_invalid_token(client):
    resp = await client.get("/api/v1/auth/invite/not-a-real-token")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_accept_invite_creates_member_login(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers)
    token = (
        await client.post(f"/api/v1/members/{member['id']}/invite", headers=headers)
    ).json()["token"]

    resp = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["user"]["role"] == "member"
    assert data["user"]["email"] == "mira@example.com"
    assert data["token"]["access_token"]

    # The new member can now log in.
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "mira@example.com",
            "password": "memberpass1",
            "tenant_slug": "zen-flow",
        },
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_accept_invite_twice_fails(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers)
    token = (
        await client.post(f"/api/v1/members/{member['id']}/invite", headers=headers)
    ).json()["token"]

    first = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reinvite_linked_member_fails(client):
    headers = await _auth_headers(client)
    member = await _create_member(client, headers)
    token = (
        await client.post(f"/api/v1/members/{member['id']}/invite", headers=headers)
    ).json()["token"]
    await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    # Member is now linked; a new invite must be rejected.
    resp = await client.post(
        f"/api/v1/members/{member['id']}/invite", headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invite_requires_staff(client):
    await _register(client)
    # No auth header -> unauthorized.
    resp = await client.post(
        "/api/v1/members/00000000-0000-0000-0000-000000000000/invite"
    )
    assert resp.status_code == 401
