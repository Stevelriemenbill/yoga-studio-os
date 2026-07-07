from datetime import UTC, datetime

import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _setup(client):
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    headers = {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}
    course = (
        await client.post(
            "/api/v1/courses",
            json={"name": "Flow", "max_participants": 10},
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
    member = (
        await client.post(
            "/api/v1/members",
            json={"first_name": "Anna", "last_name": "M"},
            headers=headers,
        )
    ).json()
    return headers, course, session, member


@pytest.mark.asyncio
async def test_notification_enqueue_and_process(client):
    headers, course, session, member = await _setup(client)
    resp = await client.post(
        "/api/v1/notifications",
        json={
            "channel": "email",
            "body": "Willkommen!",
            "member_id": member["id"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "pending"

    proc = await client.post("/api/v1/notifications/process", headers=headers)
    assert proc.status_code == 200
    assert proc.json()["sent"] == 1


@pytest.mark.asyncio
async def test_session_smart_reminders(client):
    headers, course, session, member = await _setup(client)
    # Book the member so a reminder is generated for them
    await client.post(
        "/api/v1/bookings",
        json={"session_id": session["id"], "member_id": member["id"]},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/notifications/reminders",
        json={"session_id": session["id"], "channel": "push"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    reminders = resp.json()
    assert len(reminders) == 1
    assert "Matte" in reminders[0]["body"]
    assert "Check-in" in reminders[0]["body"]


@pytest.mark.asyncio
async def test_analytics_kpis(client):
    headers, course, session, member = await _setup(client)
    await client.post(
        "/api/v1/bookings",
        json={"session_id": session["id"], "member_id": member["id"]},
        headers=headers,
    )
    resp = await client.get("/api/v1/analytics/kpis", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sessions"] == 1
    assert body["bookings"] == 1
    assert body["utilization"] == 0.1  # 1 / 10


@pytest.mark.asyncio
async def test_analytics_heatmap(client):
    headers, course, session, member = await _setup(client)
    await client.post(
        "/api/v1/bookings",
        json={"session_id": session["id"], "member_id": member["id"]},
        headers=headers,
    )
    resp = await client.get("/api/v1/analytics/heatmap", headers=headers)
    assert resp.status_code == 200
    cells = resp.json()
    assert len(cells) == 1
    assert cells[0]["level"] in ("green", "yellow", "red")
