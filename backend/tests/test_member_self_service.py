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


async def _create_session(client, headers):
    course = (
        await client.post(
            "/api/v1/courses",
            json={"name": "Flow", "max_participants": 2},
            headers=headers,
        )
    ).json()
    session = (
        await client.post(
            f"/api/v1/courses/{course['id']}/sessions",
            json={
                "course_id": course["id"],
                "starts_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            },
            headers=headers,
        )
    ).json()
    return session


async def _member_login(client, staff_headers, email="mira@example.com"):
    """Create a member, invite + accept, return (member_id, member_headers)."""
    member = (
        await client.post(
            "/api/v1/members",
            json={"first_name": "Mira", "last_name": "M", "email": email},
            headers=staff_headers,
        )
    ).json()
    token = (
        await client.post(
            f"/api/v1/members/{member['id']}/invite", headers=staff_headers
        )
    ).json()["token"]
    accepted = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    assert accepted.status_code == 201, accepted.text
    access = accepted.json()["token"]["access_token"]
    return member["id"], {"Authorization": f"Bearer {access}"}


@pytest.mark.asyncio
async def test_my_profile_returns_own_member(client):
    staff = await _staff_headers(client)
    member_id, member_headers = await _member_login(client, staff)
    resp = await client.get("/api/v1/me/profile", headers=member_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == member_id


@pytest.mark.asyncio
async def test_member_can_book_and_see_own_bookings(client):
    staff = await _staff_headers(client)
    member_id, member_headers = await _member_login(client, staff)
    session = await _create_session(client, staff)

    booked = await client.post(
        f"/api/v1/me/bookings/{session['id']}", headers=member_headers
    )
    assert booked.status_code == 201, booked.text
    assert booked.json()["member_id"] == member_id
    assert booked.json()["status"] == "booked"

    mine = await client.get("/api/v1/me/bookings", headers=member_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["session_id"] == session["id"]


@pytest.mark.asyncio
async def test_member_can_cancel_own_booking(client):
    staff = await _staff_headers(client)
    _, member_headers = await _member_login(client, staff)
    session = await _create_session(client, staff)

    booking = (
        await client.post(
            f"/api/v1/me/bookings/{session['id']}", headers=member_headers
        )
    ).json()
    cancel = await client.post(
        f"/api/v1/me/bookings/{booking['id']}/cancel", headers=member_headers
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_member_cannot_cancel_foreign_booking(client):
    staff = await _staff_headers(client)
    _, mira_headers = await _member_login(client, staff, "mira@example.com")
    other_id, _ = await _member_login(client, staff, "ben@example.com")
    session = await _create_session(client, staff)

    # Staff books the *other* member into the session.
    foreign = (
        await client.post(
            "/api/v1/bookings",
            json={"session_id": session["id"], "member_id": other_id},
            headers=staff,
        )
    ).json()

    # Mira must not be able to cancel Ben's booking.
    resp = await client.post(
        f"/api/v1/me/bookings/{foreign['id']}/cancel", headers=mira_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_member_pass_returns_qr(client):
    staff = await _staff_headers(client)
    _, member_headers = await _member_login(client, staff)
    resp = await client.get("/api/v1/me/pass", headers=member_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token"]
    assert body["qr_payload"].startswith("studioos://checkin?token=")


@pytest.mark.asyncio
async def test_staff_without_member_profile_gets_404(client):
    staff = await _staff_headers(client)
    # The admin login is not linked to a member record.
    resp = await client.get("/api/v1/me/profile", headers=staff)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/me/bookings")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_member_sees_and_registers_for_published_events(client):
    staff = await _staff_headers(client)
    _, member_headers = await _member_login(client, staff)

    now = datetime.now(UTC).replace(microsecond=0)
    # A published and an unpublished event.
    published = (
        await client.post(
            "/api/v1/events",
            json={
                "name": "Vinyasa Workshop",
                "starts_at": now.isoformat(),
                "ends_at": now.isoformat(),
                "capacity": 10,
                "is_published": True,
            },
            headers=staff,
        )
    ).json()
    await client.post(
        "/api/v1/events",
        json={
            "name": "Draft Retreat",
            "starts_at": now.isoformat(),
            "ends_at": now.isoformat(),
            "is_published": False,
        },
        headers=staff,
    )

    # Member only sees the published one.
    listing = await client.get("/api/v1/me/events", headers=member_headers)
    assert listing.status_code == 200, listing.text
    names = [e["name"] for e in listing.json()]
    assert names == ["Vinyasa Workshop"]

    # Member registers themselves.
    reg = await client.post(
        f"/api/v1/me/events/{published['id']}/register", headers=member_headers
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["status"] == "confirmed"
    registration_id = reg.json()["id"]

    mine = await client.get(
        "/api/v1/me/events/registrations", headers=member_headers
    )
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    # Member cancels their own registration.
    cancel = await client.post(
        f"/api/v1/me/events/registrations/{registration_id}/cancel",
        headers=member_headers,
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_member_cannot_register_for_unpublished_event(client):
    staff = await _staff_headers(client)
    _, member_headers = await _member_login(client, staff)
    now = datetime.now(UTC).replace(microsecond=0)
    draft = (
        await client.post(
            "/api/v1/events",
            json={
                "name": "Secret",
                "starts_at": now.isoformat(),
                "ends_at": now.isoformat(),
                "is_published": False,
            },
            headers=staff,
        )
    ).json()
    resp = await client.post(
        f"/api/v1/me/events/{draft['id']}/register", headers=member_headers
    )
    assert resp.status_code == 404
