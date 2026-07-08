import pytest

REGISTER_PAYLOAD = {
    "studio_name": "Zen Flow Studio",
    "studio_slug": "zen-flow",
    "admin_email": "admin@zenflow.example.com",
    "admin_password": "supersecret1",
    "admin_full_name": "Alex Admin",
}


async def _register(client):
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


async def _make_teacher(client, admin_headers, email="teach@example.com"):
    """Invite + accept a teacher, returning (user, headers)."""
    invite = (
        await client.post(
            "/api/v1/users/invite",
            json={"email": email, "full_name": "Tara Teacher", "role": "teacher"},
            headers=admin_headers,
        )
    ).json()
    token = _token_from_url(invite["invite_url"])
    accepted = (
        await client.post(
            "/api/v1/auth/staff-invite/accept",
            json={"token": token, "password": "teacherpass1"},
        )
    ).json()
    return accepted["user"], {
        "Authorization": f"Bearer {accepted['token']['access_token']}"
    }


@pytest.mark.asyncio
async def test_list_contacts_excludes_self(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    teacher, _ = await _make_teacher(client, admin_headers)

    contacts = await client.get("/api/v1/messages/contacts", headers=admin_headers)
    assert contacts.status_code == 200, contacts.text
    ids = [c["id"] for c in contacts.json()]
    assert teacher["id"] in ids
    assert reg["user"]["id"] not in ids


@pytest.mark.asyncio
async def test_start_conversation_and_send_message(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    teacher, teacher_headers = await _make_teacher(client, admin_headers)

    # Admin starts a conversation with the teacher.
    conv = await client.post(
        "/api/v1/messages/conversations",
        json={"recipient_id": teacher["id"]},
        headers=admin_headers,
    )
    assert conv.status_code == 201, conv.text
    conv_id = conv.json()["id"]
    assert conv.json()["other_user_id"] == teacher["id"]

    # Starting again reuses the same conversation (canonical pair).
    conv2 = await client.post(
        "/api/v1/messages/conversations",
        json={"recipient_id": reg["user"]["id"]},
        headers=teacher_headers,
    )
    assert conv2.json()["id"] == conv_id

    # Admin sends a message.
    msg = await client.post(
        f"/api/v1/messages/conversations/{conv_id}/messages",
        json={"body": "Hallo Tara!"},
        headers=admin_headers,
    )
    assert msg.status_code == 201, msg.text

    # Teacher sees it in the thread.
    thread = await client.get(
        f"/api/v1/messages/conversations/{conv_id}/messages",
        headers=teacher_headers,
    )
    assert [m["body"] for m in thread.json()] == ["Hallo Tara!"]


@pytest.mark.asyncio
async def test_unread_and_mark_read(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    teacher, teacher_headers = await _make_teacher(client, admin_headers)

    conv_id = (
        await client.post(
            "/api/v1/messages/conversations",
            json={"recipient_id": teacher["id"]},
            headers=admin_headers,
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/messages/conversations/{conv_id}/messages",
        json={"body": "Erste Nachricht"},
        headers=admin_headers,
    )

    # Teacher has one unread message.
    unread = await client.get("/api/v1/messages/unread", headers=teacher_headers)
    assert unread.json()["unread"] == 1
    # Sender has zero unread.
    admin_unread = await client.get("/api/v1/messages/unread", headers=admin_headers)
    assert admin_unread.json()["unread"] == 0

    # Teacher marks read.
    read = await client.post(
        f"/api/v1/messages/conversations/{conv_id}/read", headers=teacher_headers
    )
    assert read.status_code == 200
    assert read.json()["unread"] == 0


@pytest.mark.asyncio
async def test_conversation_list_shows_last_message(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    teacher, teacher_headers = await _make_teacher(client, admin_headers)

    conv_id = (
        await client.post(
            "/api/v1/messages/conversations",
            json={"recipient_id": teacher["id"]},
            headers=admin_headers,
        )
    ).json()["id"]
    await client.post(
        f"/api/v1/messages/conversations/{conv_id}/messages",
        json={"body": "Bis später"},
        headers=admin_headers,
    )

    convs = await client.get("/api/v1/messages/conversations", headers=teacher_headers)
    assert convs.status_code == 200, convs.text
    data = convs.json()
    assert len(data) == 1
    assert data[0]["last_message"] == "Bis später"
    assert data[0]["unread_count"] == 1


@pytest.mark.asyncio
async def test_cannot_message_self(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    resp = await client.post(
        "/api/v1/messages/conversations",
        json={"recipient_id": reg["user"]["id"]},
        headers=admin_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_participant_cannot_read(client):
    reg = await _register(client)
    admin_headers = {"Authorization": f"Bearer {reg['token']['access_token']}"}
    teacher, _ = await _make_teacher(client, admin_headers)
    _outsider, outsider_headers = await _make_teacher(
        client, admin_headers, email="out@example.com"
    )

    conv_id = (
        await client.post(
            "/api/v1/messages/conversations",
            json={"recipient_id": teacher["id"]},
            headers=admin_headers,
        )
    ).json()["id"]

    resp = await client.get(
        f"/api/v1/messages/conversations/{conv_id}/messages",
        headers=outsider_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_requires_auth(client):
    resp = await client.get("/api/v1/messages/conversations")
    assert resp.status_code == 401
