from datetime import UTC, datetime

import pytest

STUDIO = {
    "studio_name": "Zen Flow Studio",
    "studio_slug": "zen-flow",
    "admin_email": "admin@zenflow.example.com",
    "admin_password": "supersecret1",
    "admin_full_name": "Alex Admin",
}


async def _staff_headers(client):
    reg = await client.post("/api/v1/auth/register", json=STUDIO)
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}


async def _member_login(client, staff, email="mira@example.com"):
    member = (
        await client.post(
            "/api/v1/members",
            json={"first_name": "Mira", "last_name": "M", "email": email},
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
    assert accepted.status_code == 201, accepted.text
    access = accepted.json()["token"]["access_token"]
    return member["id"], {"Authorization": f"Bearer {access}"}


async def _course_and_session(client, staff, *, counts_for_training=False):
    course = (
        await client.post(
            "/api/v1/courses",
            json={
                "name": "Vinyasa",
                "max_participants": 5,
                "duration_minutes": 60,
                "counts_for_training": counts_for_training,
            },
            headers=staff,
        )
    ).json()
    # Session starting now so the check-in window is open.
    starts = datetime.now(UTC).replace(microsecond=0).isoformat()
    session = (
        await client.post(
            f"/api/v1/courses/{course['id']}/sessions",
            json={"course_id": course["id"], "starts_at": starts},
            headers=staff,
        )
    ).json()
    return course, session


async def _attend(client, staff, member_id, session):
    """Staff check-in marks the member present and the booking attended."""
    token = (
        await client.get(f"/api/v1/checkin/pass/{member_id}", headers=staff)
    ).json()["token"]
    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=staff,
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_empty_participation(client):
    staff = await _staff_headers(client)
    _, member_headers = await _member_login(client, staff)
    resp = await client.get("/api/v1/me/participation", headers=member_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "total_sessions": 0,
        "total_hours": 0.0,
        "training_hours": 0.0,
        "entries": [],
    }


@pytest.mark.asyncio
async def test_participation_counts_attended_and_hours(client):
    staff = await _staff_headers(client)
    member_id, member_headers = await _member_login(client, staff)
    _, session = await _course_and_session(client, staff)
    await _attend(client, staff, member_id, session)

    resp = await client.get("/api/v1/me/participation", headers=member_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_sessions"] == 1
    # 60-minute course => 1.0 hour.
    assert body["total_hours"] == 1.0
    # Not a training course => training hours stay 0.
    assert body["training_hours"] == 0.0
    assert body["entries"][0]["course_name"] == "Vinyasa"
    assert body["entries"][0]["counts_for_training"] is False


@pytest.mark.asyncio
async def test_participation_tracks_training_hours_separately(client):
    staff = await _staff_headers(client)
    member_id, member_headers = await _member_login(client, staff)
    _, session = await _course_and_session(
        client, staff, counts_for_training=True
    )
    await _attend(client, staff, member_id, session)

    body = (
        await client.get("/api/v1/me/participation", headers=member_headers)
    ).json()
    assert body["total_hours"] == 1.0
    assert body["training_hours"] == 1.0
    assert body["entries"][0]["counts_for_training"] is True


@pytest.mark.asyncio
async def test_participation_ignores_booked_but_not_attended(client):
    staff = await _staff_headers(client)
    member_id, member_headers = await _member_login(client, staff)
    _, session = await _course_and_session(client, staff)

    # Member books but never checks in.
    booked = await client.post(
        f"/api/v1/me/bookings/{session['id']}", headers=member_headers
    )
    assert booked.status_code == 201, booked.text

    body = (
        await client.get("/api/v1/me/participation", headers=member_headers)
    ).json()
    assert body["total_sessions"] == 0


@pytest.mark.asyncio
async def test_participation_requires_auth(client):
    resp = await client.get("/api/v1/me/participation")
    assert resp.status_code == 401
