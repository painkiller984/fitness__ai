import asyncio
import json

import httpx

from app.repositories.supabase import SupabaseGateway


def test_anonymous_sign_in_uses_publishable_key(monkeypatch) -> None:
    captured: dict = {}
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["apikey"] = request.headers.get("apikey")
        return httpx.Response(
            200,
            json={
                "user": {"id": "user-1"},
                "access_token": "access",
                "refresh_token": "refresh",
            },
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    session = asyncio.run(
        SupabaseGateway("https://example.supabase.co", "publishable").sign_in_anonymously()
    )

    assert session.user_id == "user-1"
    assert captured == {"path": "/auth/v1/signup", "apikey": "publishable"}


def test_deletion_request_erases_personal_fields(monkeypatch) -> None:
    captured: dict = {}
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    asyncio.run(SupabaseGateway("https://example.supabase.co", "publishable").request_anonymous_deletion(
        "jwt", "user-1"
    ))

    assert captured["method"] == "PATCH"
    assert captured["path"] == "/rest/v1/anonymous_profiles"
    assert captured["body"]["name"] is None
    assert captured["body"]["target_kcal"] is None
    assert captured["body"]["deletion_requested_at"]
