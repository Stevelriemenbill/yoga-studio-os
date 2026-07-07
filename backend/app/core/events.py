"""Real-time event fan-out for WebSocket live updates.

Domain code calls :func:`publish` to emit a tenant-scoped event. When Redis is
enabled the event is published to a Redis channel so that every API instance
(and the worker) can broadcast it to their locally-connected WebSocket clients.
A background listener task subscribes to Redis and forwards messages to the
in-process :class:`ConnectionManager`.

When Redis is disabled (e.g. in tests or single-instance dev) publishing falls
back to a direct in-process broadcast.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from app.core.config import settings

CHANNEL = "studio_os:events"


def _make_event(tenant_id: uuid.UUID, type_: str, payload: dict) -> dict:
    return {
        "tenant_id": str(tenant_id),
        "type": type_,
        "payload": payload,
        "ts": datetime.now(UTC).isoformat(),
    }


class ConnectionManager:
    """Tracks active WebSocket connections grouped by tenant."""

    def __init__(self) -> None:
        self._connections: dict[str, set] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, tenant_id: uuid.UUID, websocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[str(tenant_id)].add(websocket)

    async def disconnect(self, tenant_id: uuid.UUID, websocket) -> None:
        async with self._lock:
            self._connections[str(tenant_id)].discard(websocket)

    async def broadcast(self, event: dict) -> None:
        """Send an event to every WebSocket connected for its tenant."""
        tenant_id = event.get("tenant_id")
        async with self._lock:
            targets = list(self._connections.get(tenant_id, set()))
        dead = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[tenant_id].discard(ws)


manager = ConnectionManager()

# Lazily created Redis client + listener task (set in start_listener()).
_redis = None
_listener_task: asyncio.Task | None = None


def _get_redis():
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def publish(tenant_id: uuid.UUID, type_: str, payload: dict) -> None:
    """Emit a live event for a tenant.

    Uses Redis pub/sub when enabled (multi-instance safe); otherwise broadcasts
    directly to local WebSocket clients.
    """
    event = _make_event(tenant_id, type_, payload)
    if not settings.REDIS_ENABLED:
        await manager.broadcast(event)
        return
    try:
        await _get_redis().publish(CHANNEL, json.dumps(event))
    except Exception:
        # Never let a live-update failure break the request path.
        await manager.broadcast(event)


async def _listen() -> None:
    redis = _get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL)
    async for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        try:
            event = json.loads(message["data"])
        except (ValueError, KeyError):
            continue
        await manager.broadcast(event)


async def start_listener() -> None:
    """Start the Redis->local broadcast bridge (called on app startup)."""
    global _listener_task
    if not settings.REDIS_ENABLED or _listener_task is not None:
        return
    _listener_task = asyncio.create_task(_listen())


async def stop_listener() -> None:
    global _listener_task, _redis
    if _listener_task is not None:
        _listener_task.cancel()
        _listener_task = None
    if _redis is not None:
        await _redis.close()
        _redis = None
