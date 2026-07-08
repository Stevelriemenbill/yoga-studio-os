from datetime import UTC, datetime

import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _setup(client):
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    headers = {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}
    course = (
        await client.post(
            "/api/v1/courses",
            json={"name": "Yin", "max_participants": 10, "duration_minutes": 60},
            headers=headers,
        )
    ).json()
    # Session starting now so the check-in window is open.
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
            json={"first_name": "Anna", "last_name": "M"},
            headers=headers,
        )
    ).json()
    return headers, session, member


@pytest.mark.asyncio
async def test_qr_pass_and_checkin(client):
    headers, session, member = await _setup(client)

    # Get pass token
    passq = await client.get(f"/api/v1/checkin/pass/{member['id']}", headers=headers)
    assert passq.status_code == 200
    token = passq.json()["token"]

    # QR check-in
    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    # Double check-in blocked (anti-abuse)
    resp2 = await client.post(
        "/api/v1/checkin/qr",
        json={"token": token, "session_id": session["id"]},
        headers=headers,
    )
    assert resp2.status_code == 409

    # Attendance now reflects the check-in
    att = await client.get(
        f"/api/v1/attendance/session/{session['id']}", headers=headers
    )
    assert att.status_code == 200
    assert len(att.json()) == 1
    assert att.json()[0]["status"] in ("present", "late")


@pytest.mark.asyncio
async def test_qr_full_payload_accepted(client):
    """A camera scans the full ``studioos://checkin?token=...`` payload."""
    headers, session, member = await _setup(client)
    passq = await client.get(f"/api/v1/checkin/pass/{member['id']}", headers=headers)
    payload = passq.json()["qr_payload"]
    assert payload.startswith("studioos://checkin?token=")

    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": payload, "session_id": session["id"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_invalid_qr_token_rejected(client):
    headers, session, member = await _setup(client)
    resp = await client.post(
        "/api/v1/checkin/qr",
        json={"token": "deadbeef.forged", "session_id": session["id"]},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_manual_attendance_override(client):
    headers, session, member = await _setup(client)
    resp = await client.put(
        f"/api/v1/attendance/session/{session['id']}",
        json={"member_id": member["id"], "status": "excused"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "excused"


@pytest.mark.asyncio
async def test_training_hours_and_dashboard(client):
    headers, session, member = await _setup(client)

    # Requirement: 200 practice hours
    await client.post(
        "/api/v1/training/requirements",
        json={"name": "RYT200 Practice", "area": "practice", "required_hours": 200},
        headers=headers,
    )
    # Log 40 practice hours
    r = await client.post(
        "/api/v1/training/hours",
        json={
            "trainee_id": member["id"],
            "area": "practice",
            "hours": 40,
            "entry_date": "2030-01-01",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text

    dash = await client.get(
        f"/api/v1/training/dashboard/{member['id']}", headers=headers
    )
    assert dash.status_code == 200
    body = dash.json()
    assert body["total_completed"] == 40
    practice = next(b for b in body["breakdown"] if b["area"] == "practice")
    assert practice["required_hours"] == 200
    assert practice["progress"] == 0.2

    # CSV export
    csv_resp = await client.get(
        f"/api/v1/training/export/{member['id']}.csv", headers=headers
    )
    assert csv_resp.status_code == 200
    assert "practice" in csv_resp.text
