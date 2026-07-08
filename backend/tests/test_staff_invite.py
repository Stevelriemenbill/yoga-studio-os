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


async def _admin_headers(client):
    reg = await _register(client)
    return {"Authorization": f"Bearer {reg['token']['access_token']}"}


def _token_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


@pytest.mark.asyncio
async def test_invite_teacher_returns_link(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/users/invite",
        json={"email": "teach@example.com", "full_name": "Tara Teacher", "role": "teacher"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "/staff-invite/" in data["invite_url"]
    assert data["email_delivered"] is False
    assert data["invite"]["role"] == "teacher"
    assert data["invite"]["status"] == "pending"


@pytest.mark.asyncio
async def test_invite_rejects_member_role(client):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/v1/users/invite",
        json={"email": "x@example.com", "role": "member"},
        headers=headers,
    )
    assert resp.status_code == 422  # schema validation rejects the role


@pytest.mark.asyncio
async def test_invite_requires_admin(client):
    # A teacher (staff, not admin) must not be able to invite staff.
    admin_headers = await _admin_headers(client)
    invite = (
        await client.post(
            "/api/v1/users/invite",
            json={"email": "teach@example.com", "role": "teacher"},
            headers=admin_headers,
        )
    ).json()
    token = _token_from_url(invite["invite_url"])
    teacher = await client.post(
        "/api/v1/auth/staff-invite/accept",
        json={"token": token, "password": "teacherpass1"},
    )
    teacher_headers = {
        "Authorization": f"Bearer {teacher.json()['token']['access_token']}"
    }
    resp = await client.post(
        "/api/v1/users/invite",
        json={"email": "other@example.com", "role": "reception"},
        headers=teacher_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_preview_and_accept_staff_invite(client):
    headers = await _admin_headers(client)
    invite = (
        await client.post(
            "/api/v1/users/invite",
            json={"email": "teach@example.com", "full_name": "Tara", "role": "teacher"},
            headers=headers,
        )
    ).json()
    token = _token_from_url(invite["invite_url"])

    preview = await client.get(f"/api/v1/auth/staff-invite/{token}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["email"] == "teach@example.com"
    assert preview.json()["role"] == "teacher"
    assert preview.json()["studio_name"] == "Zen Flow Studio"

    accepted = await client.post(
        "/api/v1/auth/staff-invite/accept",
        json={"token": token, "password": "teacherpass1"},
    )
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["user"]["role"] == "teacher"

    # The new teacher can log in.
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "teach@example.com",
            "password": "teacherpass1",
            "tenant_slug": "zen-flow",
        },
    )
    assert login.status_code == 200, login.text


@pytest.mark.asyncio
async def test_accept_staff_invite_twice_fails(client):
    headers = await _admin_headers(client)
    invite = (
        await client.post(
            "/api/v1/users/invite",
            json={"email": "teach@example.com", "role": "teacher"},
            headers=headers,
        )
    ).json()
    token = _token_from_url(invite["invite_url"])
    first = await client.post(
        "/api/v1/auth/staff-invite/accept",
        json={"token": token, "password": "teacherpass1"},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/auth/staff-invite/accept",
        json={"token": token, "password": "teacherpass1"},
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_open_invite_fails(client):
    headers = await _admin_headers(client)
    payload = {"email": "teach@example.com", "role": "teacher"}
    first = await client.post("/api/v1/users/invite", json=payload, headers=headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/users/invite", json=payload, headers=headers)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_list_and_revoke_staff(client):
    headers = await _admin_headers(client)
    invite = (
        await client.post(
            "/api/v1/users/invite",
            json={"email": "teach@example.com", "role": "teacher"},
            headers=headers,
        )
    ).json()

    listing = await client.get("/api/v1/users", headers=headers)
    assert listing.status_code == 200, listing.text
    entries = listing.json()
    # admin user + pending invite
    kinds = {e["kind"] for e in entries}
    assert "user" in kinds and "invite" in kinds
    pending = [e for e in entries if e["kind"] == "invite"]
    assert pending[0]["email"] == "teach@example.com"

    invite_id = invite["invite"]["id"]
    revoke = await client.delete(
        f"/api/v1/users/invite/{invite_id}", headers=headers
    )
    assert revoke.status_code == 204

    # After revoke the invite no longer appears as pending.
    after = await client.get("/api/v1/users", headers=headers)
    assert not [e for e in after.json() if e["kind"] == "invite"]
