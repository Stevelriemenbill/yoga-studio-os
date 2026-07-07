import uuid

import pytest

from app.core import events


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


@pytest.mark.asyncio
async def test_manager_broadcasts_to_tenant_only():
    manager = events.ConnectionManager()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()

    await manager.connect(tenant_a, ws_a)
    await manager.connect(tenant_b, ws_b)
    assert ws_a.accepted and ws_b.accepted

    event = events._make_event(tenant_a, "booking.created", {"x": 1})
    await manager.broadcast(event)

    assert len(ws_a.sent) == 1
    assert ws_a.sent[0]["type"] == "booking.created"
    assert ws_b.sent == []  # isolated by tenant


@pytest.mark.asyncio
async def test_publish_inprocess_when_redis_disabled(monkeypatch):
    # REDIS_ENABLED is false in tests -> publish() broadcasts locally.
    tenant = uuid.uuid4()
    ws = FakeWebSocket()
    await events.manager.connect(tenant, ws)
    try:
        await events.publish(tenant, "test.event", {"ok": True})
        assert any(e["type"] == "test.event" for e in ws.sent)
    finally:
        await events.manager.disconnect(tenant, ws)


@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    manager = events.ConnectionManager()
    tenant = uuid.uuid4()
    ws = FakeWebSocket()
    await manager.connect(tenant, ws)
    await manager.disconnect(tenant, ws)
    await manager.broadcast(events._make_event(tenant, "x", {}))
    assert ws.sent == []
