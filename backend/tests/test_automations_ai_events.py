from datetime import UTC, datetime, timedelta

import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _auth(client):
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    return {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}


# --- Automations -----------------------------------------------------------


@pytest.mark.asyncio
async def test_inactivity_automation_enqueues(client):
    headers = await _auth(client)
    await client.post(
        "/api/v1/members",
        json={"first_name": "Lena", "last_name": "K"},
        headers=headers,
    )
    rule = await client.post(
        "/api/v1/automations",
        json={
            "name": "Reaktivierung",
            "trigger": "inactive_days",
            "threshold_days": 30,
            "channel": "email",
            "message_template": "Hallo {first_name}, wir vermissen dich!",
        },
        headers=headers,
    )
    assert rule.status_code == 201, rule.text

    run = await client.post("/api/v1/automations/run", headers=headers)
    assert run.status_code == 200, run.text
    # Member has no bookings -> considered inactive -> one message enqueued.
    assert run.json()["total_enqueued"] == 1


# --- AI --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_assistant_answers(client):
    headers = await _auth(client)
    resp = await client.post(
        "/api/v1/ai/assistant",
        json={"question": "Wie ist die Auslastung?"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["type"] == "assistant_answer"
    assert "Auslastung" in body["body"]


@pytest.mark.asyncio
async def test_ai_forecast_empty(client):
    headers = await _auth(client)
    resp = await client.get("/api/v1/ai/forecast", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


# --- Events ----------------------------------------------------------------


async def _make_event(client, headers, capacity=1, requires_deposit=False):
    now = datetime.now(UTC).replace(microsecond=0)
    return (
        await client.post(
            "/api/v1/events",
            json={
                "name": "Retreat",
                "type": "retreat",
                "starts_at": (now + timedelta(days=10)).isoformat(),
                "ends_at": (now + timedelta(days=12)).isoformat(),
                "capacity": capacity,
                "price_cents": 20000,
                "requires_deposit": requires_deposit,
                "deposit_cents": 5000,
            },
            headers=headers,
        )
    ).json()


async def _make_member(client, headers, first="Max"):
    return (
        await client.post(
            "/api/v1/members",
            json={"first_name": first, "last_name": "M"},
            headers=headers,
        )
    ).json()


@pytest.mark.asyncio
async def test_event_registration_and_waitlist(client):
    headers = await _auth(client)
    event = await _make_event(client, headers, capacity=1)
    m1 = await _make_member(client, headers, "Ann")
    m2 = await _make_member(client, headers, "Bea")

    r1 = await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"member_id": m1["id"]},
        headers=headers,
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["status"] == "confirmed"

    r2 = await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"member_id": m2["id"]},
        headers=headers,
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "waitlisted"

    # Cancel first -> waitlisted should be promoted to confirmed.
    cancel = await client.delete(
        f"/api/v1/events/registrations/{r1.json()['id']}",
        headers=headers,
    )
    assert cancel.status_code == 200

    regs = (
        await client.get(
            f"/api/v1/events/{event['id']}/registrations", headers=headers
        )
    ).json()
    promoted = next(r for r in regs if r["member_id"] == m2["id"])
    assert promoted["status"] == "confirmed"


@pytest.mark.asyncio
async def test_event_deposit_flow(client):
    headers = await _auth(client)
    event = await _make_event(client, headers, capacity=5, requires_deposit=True)
    member = await _make_member(client, headers)

    reg = await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"member_id": member["id"]},
        headers=headers,
    )
    assert reg.json()["status"] == "pending"

    paid = await client.post(
        f"/api/v1/events/registrations/{reg.json()['id']}/pay",
        json={"amount_cents": 5000},
        headers=headers,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "confirmed"
    assert paid.json()["amount_paid_cents"] == 5000


@pytest.mark.asyncio
async def test_event_duplicate_registration_rejected(client):
    headers = await _auth(client)
    event = await _make_event(client, headers, capacity=5)
    member = await _make_member(client, headers)
    await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"member_id": member["id"]},
        headers=headers,
    )
    dup = await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"member_id": member["id"]},
        headers=headers,
    )
    assert dup.status_code == 409
