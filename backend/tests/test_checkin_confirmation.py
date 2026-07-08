from datetime import UTC, datetime

import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _staff_setup(client):
    """Register a studio (admin) and create a course session + member."""
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    headers = {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}
    course = (
        await client.post(
            "/api/v1/courses",
            json={"name": "Yin", "max_participants": 10, "duration_minutes": 60},
            headers=headers,
        )
    ).json()
    starts = datetime.now(UTC).replace(microsecond=0).isoformat()
    session = (
        await client.post(
            f"/api/v1/courses/{course['id']}/sessions",
            json={"course_id": course["id"], "starts_at": starts},
            headers=headers,
        )
    ).json()
    member = (
        await client.post(
            "/api/v1/members",
            json={
                "first_name": "Anna",
                "last_name": "M",
                "email": "anna@example.com",
            },
            headers=headers,
        )
    ).json()
    return headers, session, member


async def _member_login_headers(client, staff_headers, member):
    """Invite the member, accept it, and return the member's auth headers."""
    token = (
        await client.post(
            f"/api/v1/members/{member['id']}/invite", headers=staff_headers
        )
    ).json()["token"]
    accept = await client.post(
        "/api/v1/auth/invite/accept",
        json={"token": token, "password": "memberpass1"},
    )
    access = accept.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {access}"}


async def _pass_token(client, headers, member_id):
    resp = await client.get(f"/api/v1/checkin/pass/{member_id}", headers=headers)
    return resp.json()["token"]


@pytest.mark.asyncio
async def test_self_checkin_creates_pending_attendance(client):
    staff_headers, session, member = await _staff_setup(client)
    member_headers = await _member_login_headers(client, staff_headers, member)

    token = await _pass_token(client, staff_headers, member["id"])
    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=member_headers,
    )
    assert resp.status_code == 201, resp.text

    att = (
        await client.get(
            f"/api/v1/attendance/session/{session['id']}", headers=staff_headers
        )
    ).json()
    assert len(att) == 1
    assert att[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_staff_checkin_counts_immediately(client):
    staff_headers, session, member = await _staff_setup(client)
    token = await _pass_token(client, staff_headers, member["id"])
    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=staff_headers,
    )
    assert resp.status_code == 201, resp.text

    att = (
        await client.get(
            f"/api/v1/attendance/session/{session['id']}", headers=staff_headers
        )
    ).json()
    assert att[0]["status"] in ("present", "late")


@pytest.mark.asyncio
async def test_pending_listed_and_confirmed(client):
    staff_headers, session, member = await _staff_setup(client)
    member_headers = await _member_login_headers(client, staff_headers, member)
    token = await _pass_token(client, staff_headers, member["id"])
    await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=member_headers,
    )

    # Pending list shows the self check-in.
    pending = await client.get("/api/v1/attendance/pending", headers=staff_headers)
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    assert pending.json()[0]["member_id"] == member["id"]

    # Staff confirms it.
    confirm = await client.post(
        f"/api/v1/attendance/session/{session['id']}/confirm",
        json={"member_id": member["id"]},
        headers=staff_headers,
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] in ("present", "late")

    # No longer pending.
    pending2 = await client.get("/api/v1/attendance/pending", headers=staff_headers)
    assert pending2.json() == []


@pytest.mark.asyncio
async def test_pending_rejected_marks_absent(client):
    staff_headers, session, member = await _staff_setup(client)
    member_headers = await _member_login_headers(client, staff_headers, member)
    token = await _pass_token(client, staff_headers, member["id"])
    await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=member_headers,
    )

    reject = await client.post(
        f"/api/v1/attendance/session/{session['id']}/reject",
        json={"member_id": member["id"]},
        headers=staff_headers,
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "absent"


@pytest.mark.asyncio
async def test_confirm_requires_pending(client):
    staff_headers, session, member = await _staff_setup(client)
    # Staff check-in -> already present, not pending.
    token = await _pass_token(client, staff_headers, member["id"])
    await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=staff_headers,
    )
    resp = await client.post(
        f"/api/v1/attendance/session/{session['id']}/confirm",
        json={"member_id": member["id"]},
        headers=staff_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_member_cannot_confirm(client):
    staff_headers, session, member = await _staff_setup(client)
    member_headers = await _member_login_headers(client, staff_headers, member)
    token = await _pass_token(client, staff_headers, member["id"])
    await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=member_headers,
    )
    # Member tries to confirm their own pending check-in -> forbidden.
    resp = await client.post(
        f"/api/v1/attendance/session/{session['id']}/confirm",
        json={"member_id": member["id"]},
        headers=member_headers,
    )
    assert resp.status_code == 403
