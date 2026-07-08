import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _auth_headers(client) -> dict:
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = reg.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _make_course(client, headers, **overrides):
    payload = {
        "name": "Vinyasa Flow",
        "level": "all",
        "max_participants": 2,
        "min_participants": 1,
        "duration_minutes": 60,
        **overrides,
    }
    resp = await client.post("/api/v1/courses", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_session(client, headers, course_id, starts_at="2030-01-01T18:00:00"):
    resp = await client.post(
        f"/api/v1/courses/{course_id}/sessions",
        json={"course_id": course_id, "starts_at": starts_at},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_member(client, headers, first="Anna", last="Muster"):
    resp = await client.post(
        "/api/v1/members",
        json={"first_name": first, "last_name": last},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_course_session_crud(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)
    session = await _make_session(client, headers, course["id"])
    assert session["capacity"] == 2

    # Session appears in calendar range
    resp = await client.get(
        "/api/v1/sessions",
        params={"start": "2030-01-01T00:00:00", "end": "2030-01-02T00:00:00"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["available_spots"] == 2


@pytest.mark.asyncio
async def test_recurring_schedule_generates_sessions(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [0, 2],  # Monday, Wednesday
            "start_time": "18:00:00",
            "start_date": "2030-01-07",  # a Monday
            "end_date": "2030-01-20",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    # Two full weeks, Mon+Wed => 4 sessions
    assert len(resp.json()) == 4


@pytest.mark.asyncio
async def test_recurring_schedule_by_count(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [0, 2, 4],  # Mon, Wed, Fri
            "start_time": "09:00:00",
            "start_date": "2030-01-07",  # a Monday
            "count": 5,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert len(resp.json()) == 5


@pytest.mark.asyncio
async def test_recurring_schedule_requires_exactly_one_end(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)
    # Neither end_date nor count -> 422
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [0],
            "start_time": "18:00:00",
            "start_date": "2030-01-07",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    # Both end_date and count -> 422
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [0],
            "start_time": "18:00:00",
            "start_date": "2030-01-07",
            "end_date": "2030-02-07",
            "count": 3,
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recurring_schedule_rejects_invalid_weekday(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/schedule",
        json={
            "course_id": course["id"],
            "weekdays": [7],  # invalid
            "start_time": "18:00:00",
            "start_date": "2030-01-07",
            "count": 3,
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_booking_fills_capacity_then_full(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers, max_participants=1)
    session = await _make_session(client, headers, course["id"])
    m1 = await _make_member(client, headers, "Anna")
    m2 = await _make_member(client, headers, "Bea")

    r1 = await client.post(
        "/api/v1/bookings",
        json={"session_id": session["id"], "member_id": m1["id"]},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text

    r2 = await client.post(
        "/api/v1/bookings",
        json={"session_id": session["id"], "member_id": m2["id"]},
        headers=headers,
    )
    assert r2.status_code == 409  # full


@pytest.mark.asyncio
async def test_cancel_promotes_waitlist(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers, max_participants=1)
    session = await _make_session(client, headers, course["id"])
    m1 = await _make_member(client, headers, "Anna")
    m2 = await _make_member(client, headers, "Bea")

    booking = (
        await client.post(
            "/api/v1/bookings",
            json={"session_id": session["id"], "member_id": m1["id"]},
            headers=headers,
        )
    ).json()

    # m2 joins waitlist since session is full
    wl = await client.post(
        "/api/v1/waitlist",
        json={"session_id": session["id"], "member_id": m2["id"]},
        headers=headers,
    )
    assert wl.status_code == 201, wl.text

    # Cancel m1 -> should offer the spot to m2
    cancel = await client.post(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=headers
    )
    assert cancel.status_code == 200

    entries = await client.get(
        f"/api/v1/waitlist/session/{session['id']}", headers=headers
    )
    # m2 no longer "waiting" (moved to offered)
    waiting = [e for e in entries.json() if e["status"] == "waiting"]
    assert len(waiting) == 0


@pytest.mark.asyncio
async def test_rebook_moves_member(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers, max_participants=5)
    s1 = await _make_session(client, headers, course["id"], "2030-01-01T18:00:00")
    s2 = await _make_session(client, headers, course["id"], "2030-01-02T18:00:00")
    m1 = await _make_member(client, headers)

    booking = (
        await client.post(
            "/api/v1/bookings",
            json={"session_id": s1["id"], "member_id": m1["id"]},
            headers=headers,
        )
    ).json()

    rebook = await client.post(
        f"/api/v1/bookings/{booking['id']}/rebook",
        json={"new_session_id": s2["id"]},
        headers=headers,
    )
    assert rebook.status_code == 200, rebook.text
    assert rebook.json()["session_id"] == s2["id"]
    assert rebook.json()["source"] == "rebooked"


@pytest.mark.asyncio
async def test_cancel_session_cancels_bookings_and_notifies(client):
    """Cancelling a session cancels active bookings and queues notifications."""
    headers = await _auth_headers(client)
    course = await _make_course(client, headers, max_participants=5)
    session = await _make_session(client, headers, course["id"])
    m1 = await _make_member(client, headers, "Anna")
    m2 = await _make_member(client, headers, "Bea")
    for m in (m1, m2):
        r = await client.post(
            "/api/v1/bookings",
            json={"session_id": session["id"], "member_id": m["id"]},
            headers=headers,
        )
        assert r.status_code == 201, r.text

    resp = await client.post(
        f"/api/v1/sessions/{session['id']}/cancel",
        json={"reason": "Lehrer krank"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancellation_reason"] == "Lehrer krank"

    # No active bookings remain for the session.
    bookings = (
        await client.get(
            f"/api/v1/bookings/session/{session['id']}", headers=headers
        )
    ).json()
    assert bookings == []

    # A notification was queued for each affected member.
    notes = (await client.get("/api/v1/notifications", headers=headers)).json()
    member_ids = {n["member_id"] for n in notes if n.get("template") == "session_cancelled"}
    assert {m1["id"], m2["id"]} <= member_ids


@pytest.mark.asyncio
async def test_session_inherits_and_overrides_location(client):
    """A session inherits the course location/online unless it overrides."""
    headers = await _auth_headers(client)
    course = await _make_course(
        client,
        headers,
        location="Studio Raum 1",
        is_online=False,
    )
    # Session without overrides -> inherits course location.
    s1 = await _make_session(client, headers, course["id"])
    assert s1["effective_location"] == "Studio Raum 1"
    assert s1["effective_is_online"] is False

    # Session with online override.
    resp = await client.post(
        f"/api/v1/courses/{course['id']}/sessions",
        json={
            "course_id": course["id"],
            "starts_at": "2030-02-01T18:00:00",
            "is_online": True,
            "online_url": "https://zoom.us/j/123",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    s2 = resp.json()
    assert s2["effective_is_online"] is True
    assert s2["effective_online_url"] == "https://zoom.us/j/123"
    # Raw override recorded, course location still inherited for location.
    assert s2["is_online"] is True
    assert s2["effective_location"] == "Studio Raum 1"


@pytest.mark.asyncio
async def test_course_attachment_upload_list_delete(client):
    headers = await _auth_headers(client)
    course = await _make_course(client, headers)

    up = await client.post(
        f"/api/v1/courses/{course['id']}/attachments",
        files={"file": ("info.txt", b"Anmeldeinfos hier", "text/plain")},
        headers=headers,
    )
    assert up.status_code == 201, up.text
    att = up.json()
    assert att["filename"] == "info.txt"
    assert att["size_bytes"] == len(b"Anmeldeinfos hier")
    assert att["url"].startswith("/media/courses/")

    lst = await client.get(
        f"/api/v1/courses/{course['id']}/attachments", headers=headers
    )
    assert lst.status_code == 200
    assert len(lst.json()) == 1

    dele = await client.delete(
        f"/api/v1/courses/{course['id']}/attachments/{att['id']}", headers=headers
    )
    assert dele.status_code == 204

    lst2 = await client.get(
        f"/api/v1/courses/{course['id']}/attachments", headers=headers
    )
    assert lst2.json() == []


@pytest.mark.asyncio
async def test_tenant_isolation(client):
    """A member from tenant A must not be visible/bookable in tenant B."""
    headers_a = await _auth_headers(client)
    member_a = await _make_member(client, headers_a)

    # Second tenant
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "studio_slug": "other", "studio_name": "Other"},
    )
    headers_b = {"Authorization": f"Bearer {reg_b.json()['token']['access_token']}"}

    # Tenant B cannot see tenant A's member
    resp = await client.get(f"/api/v1/members/{member_a['id']}", headers=headers_b)
    assert resp.status_code == 404
