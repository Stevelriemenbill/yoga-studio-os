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


JOIN_PAYLOAD = {
    "first_name": "Nora",
    "last_name": "Newcomer",
    "email": "nora@example.com",
    "phone": "+49 111",
    "message": "Ich möchte gern Yoga ausprobieren.",
}


@pytest.mark.asyncio
async def test_public_studio_lookup(client):
    await _register(client)
    resp = await client.get("/api/v1/join/zen-flow")
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Zen Flow Studio"


@pytest.mark.asyncio
async def test_public_studio_unknown_slug(client):
    resp = await client.get("/api/v1/join/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_join_request(client):
    await _register(client)
    resp = await client.post("/api/v1/join/zen-flow", json=JOIN_PAYLOAD)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "nora@example.com"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_duplicate_submit_is_idempotent(client):
    await _register(client)
    first = await client.post("/api/v1/join/zen-flow", json=JOIN_PAYLOAD)
    second = await client.post("/api/v1/join/zen-flow", json=JOIN_PAYLOAD)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_submit_requires_no_auth_but_valid_studio(client):
    resp = await client.post("/api/v1/join/nope", json=JOIN_PAYLOAD)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_and_approve_flow(client):
    headers = await _admin_headers(client)
    await client.post("/api/v1/join/zen-flow", json=JOIN_PAYLOAD)

    listing = await client.get("/api/v1/join-requests", headers=headers)
    assert listing.status_code == 200, listing.text
    reqs = listing.json()
    assert len(reqs) == 1
    request_id = reqs[0]["id"]

    approve = await client.post(
        f"/api/v1/join-requests/{request_id}/approve", headers=headers
    )
    assert approve.status_code == 200, approve.text
    assert "/invite/" in approve.json()["invite_url"]

    # A member now exists and appears in the members list.
    members = await client.get("/api/v1/members", headers=headers)
    emails = [m["email"] for m in members.json()]
    assert "nora@example.com" in emails

    # Request is no longer pending -> approving again fails.
    again = await client.post(
        f"/api/v1/join-requests/{request_id}/approve", headers=headers
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_decline_flow(client):
    headers = await _admin_headers(client)
    await client.post("/api/v1/join/zen-flow", json=JOIN_PAYLOAD)
    request_id = (
        await client.get("/api/v1/join-requests", headers=headers)
    ).json()[0]["id"]

    decline = await client.post(
        f"/api/v1/join-requests/{request_id}/decline", headers=headers
    )
    assert decline.status_code == 200
    assert decline.json()["status"] == "declined"

    # No member created.
    members = await client.get("/api/v1/members", headers=headers)
    assert members.json() == []


@pytest.mark.asyncio
async def test_list_requires_staff(client):
    resp = await client.get("/api/v1/join-requests")
    assert resp.status_code == 401
