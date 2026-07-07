import pytest

from tests.test_auth import REGISTER_PAYLOAD


async def _auth(client):
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    return {"Authorization": f"Bearer {reg.json()['token']['access_token']}"}


@pytest.mark.asyncio
async def test_api_key_lifecycle(client):
    headers = await _auth(client)
    created = await client.post(
        "/api/v1/integrations/api-keys",
        json={"name": "Zapier"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["key"].startswith("sk_")  # plaintext returned once
    assert body["prefix"] == body["key"][:8]

    listed = await client.get("/api/v1/integrations/api-keys", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    # Plaintext must not be present in listings.
    assert "key" not in listed.json()[0]

    revoke = await client.delete(
        f"/api/v1/integrations/api-keys/{body['id']}", headers=headers
    )
    assert revoke.status_code == 204


@pytest.mark.asyncio
async def test_webhook_create_and_list(client):
    headers = await _auth(client)
    created = await client.post(
        "/api/v1/integrations/webhooks",
        json={
            "url": "https://example.com/hook",
            "event_types": ["booking.created"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["event_types"] == ["booking.created"]

    listed = await client.get("/api/v1/integrations/webhooks", headers=headers)
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_branding_update(client):
    headers = await _auth(client)
    resp = await client.patch(
        "/api/v1/integrations/branding",
        json={"brand_primary_color": "#10b981", "custom_domain": "yoga.example.com"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["brand_primary_color"] == "#10b981"
    assert resp.json()["custom_domain"] == "yoga.example.com"


@pytest.mark.asyncio
async def test_webhook_signature_is_deterministic():
    from app.services.integrations import sign_payload

    body = b'{"type":"booking.created","data":{}}'
    sig1 = sign_payload("secret", body)
    sig2 = sign_payload("secret", body)
    assert sig1 == sig2
    assert sign_payload("other", body) != sig1
