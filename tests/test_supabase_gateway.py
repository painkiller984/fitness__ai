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
    captured: list[dict] = []
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append({
            "method": request.method,
            "path": request.url.path,
            "body": json.loads(request.content) if request.content else None,
        })
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

    assert [(item["method"], item["path"]) for item in captured] == [
        ("DELETE", "/rest/v1/plans"),
        ("DELETE", "/rest/v1/progress_entries"),
        ("DELETE", "/rest/v1/profiles"),
        ("PATCH", "/rest/v1/anonymous_profiles"),
    ]
    body = captured[-1]["body"]
    assert body["name"] is None
    assert body["target_kcal"] is None
    assert body["medical_notes"] == ""
    assert body["is_pregnant"] is False
    assert body["deletion_requested_at"]


def test_generated_plan_is_saved_under_users_rls_identity(monkeypatch) -> None:
    captured: list[dict] = []
    original_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        item = {
            "method": request.method,
            "path": request.url.path,
            "authorization": request.headers.get("authorization"),
            "body": json.loads(request.content),
        }
        captured.append(item)
        if request.method == "PATCH":
            return httpx.Response(204)
        return httpx.Response(201, json=[{"id": 1, **item["body"]}])

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs)
    )
    asyncio.run(
        SupabaseGateway("https://example.supabase.co", "publishable").save_plan(
            "jwt", "user-1", "workout", {"markdown": "plan"}, "workout-v1"
        )
    )

    assert [item["method"] for item in captured] == ["PATCH", "POST"]
    assert all(item["path"] == "/rest/v1/plans" for item in captured)
    assert captured[0]["body"] == {"status": "archived"}
    assert captured[1]["authorization"] == "Bearer jwt"
    assert captured[1]["body"]["user_id"] == "user-1"
    assert captured[1]["body"]["kind"] == "workout"
    assert captured[1]["body"]["calculation_version"] == "workout-v1"
