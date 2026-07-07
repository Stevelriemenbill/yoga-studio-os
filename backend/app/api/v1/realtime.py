import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.events import manager
from app.core.security import decode_token

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def realtime(websocket: WebSocket, token: str = Query(...)) -> None:
    """Tenant-scoped live update stream.

    Clients connect with ``?token=<access_token>`` and receive JSON events for
    their tenant: bookings, waitlist promotions, check-ins, notifications, etc.
    """
    try:
        payload = decode_token(token, expected_type="access")
        tenant_id = payload.get("tid")
        if tenant_id is None:
            await websocket.close(code=4401)
            return
        tenant_uuid = uuid.UUID(tenant_id)
    except (JWTError, ValueError):
        await websocket.close(code=4401)
        return

    await manager.connect(tenant_uuid, websocket)
    try:
        while True:
            # We don't expect client messages; keep the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(tenant_uuid, websocket)
    except Exception:
        await manager.disconnect(tenant_uuid, websocket)
