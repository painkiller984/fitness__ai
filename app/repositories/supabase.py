from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.agent.state import UserProfile


class SupabaseError(RuntimeError):
    pass


@dataclass(slots=True)
class AuthSession:
    user_id: str
    email: str
    access_token: str
    refresh_token: str


class SupabaseGateway:
    """Minimal Supabase Auth/Data API client using a user's JWT so RLS stays active."""

    def __init__(self, url: str, publishable_key: str) -> None:
        self.url = url.rstrip("/")
        self.key = publishable_key

    def _headers(self, access_token: str | None = None) -> dict[str, str]:
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def sign_in(self, email: str, password: str) -> AuthSession:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/auth/v1/token?grant_type=password",
                headers=self._headers(),
                json={"email": email, "password": password},
            )
        data = self._unwrap(response)
        return self._session(data)

    async def sign_up(self, email: str, password: str) -> AuthSession | None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/auth/v1/signup",
                headers=self._headers(),
                json={"email": email, "password": password},
            )
        data = self._unwrap(response)
        if not data.get("access_token"):
            return None
        return self._session(data)

    async def sign_in_anonymously(self) -> AuthSession:
        """Creates an anonymous Supabase Auth user when Anonymous Sign-Ins are enabled."""
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/auth/v1/signup", headers=self._headers(), json={"data": {}}
            )
        return self._session(self._unwrap(response))

    async def refresh_session(self, refresh_token: str) -> AuthSession:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/auth/v1/token?grant_type=refresh_token",
                headers=self._headers(),
                json={"refresh_token": refresh_token},
            )
        return self._session(self._unwrap(response))

    async def get_anonymous_profile(self, access_token: str, user_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.url}/rest/v1/anonymous_profiles",
                headers=self._headers(access_token),
                params={"user_id": f"eq.{user_id}", "select": "*", "limit": "1"},
            )
        rows = self._unwrap(response)
        return rows[0] if rows else None

    async def save_anonymous_facts(
        self, access_token: str, user_id: str, facts: dict[str, Any]
    ) -> dict[str, Any]:
        headers = self._headers(access_token)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        payload = {"user_id": user_id, **facts}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/rest/v1/anonymous_profiles",
                headers=headers,
                params={"on_conflict": "user_id"},
                json=payload,
            )
        rows = self._unwrap(response)
        return rows[0]

    async def request_anonymous_deletion(self, access_token: str, user_id: str) -> None:
        """Erase profile fields now; the scheduled job removes the Auth user permanently."""
        headers = self._headers(access_token)
        headers["Prefer"] = "return=minimal"
        payload = {
            "name": None,
            "age": None,
            "sex": None,
            "height_cm": None,
            "weight_kg": None,
            "goal": None,
            "activity_level": None,
            "training_place": None,
            "training_experience": None,
            "training_days_per_week": None,
            "available_equipment": [],
            "equipment_screened": False,
            "health_screened": False,
            "dietary_preferences": [],
            "allergies": [],
            "injuries": [],
            "target_kcal": None,
            "protein_g": None,
            "fat_g": None,
            "carbs_g": None,
            "deletion_requested_at": datetime.now(UTC).isoformat(),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{self.url}/rest/v1/anonymous_profiles",
                headers=headers,
                params={"user_id": f"eq.{user_id}"},
                json=payload,
            )
        self._unwrap(response)

    async def touch_anonymous_profile(self, access_token: str, user_id: str) -> dict[str, Any] | None:
        headers = self._headers(access_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{self.url}/rest/v1/anonymous_profiles",
                headers=headers,
                params={"user_id": f"eq.{user_id}"},
                json={"last_active_at": datetime.now(UTC).isoformat()},
            )
        rows = self._unwrap(response)
        return rows[0] if rows else None

    async def get_profile(self, access_token: str, user_id: str) -> UserProfile | None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.url}/rest/v1/profiles",
                headers=self._headers(access_token),
                params={"user_id": f"eq.{user_id}", "select": "*", "limit": "1"},
            )
        rows = self._unwrap(response)
        return UserProfile.model_validate(rows[0]) if rows else None

    async def save_profile(self, access_token: str, profile: UserProfile) -> UserProfile:
        headers = self._headers(access_token)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        payload = profile.model_dump(mode="json")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.url}/rest/v1/profiles", headers=headers, json=payload
            )
        rows = self._unwrap(response)
        return UserProfile.model_validate(rows[0])

    @staticmethod
    def _unwrap(response: httpx.Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            data = {"message": response.text or "Supabase вернул пустой ответ."}
        if response.is_error:
            message = data.get("msg") or data.get("message") or data.get("error_description")
            raise SupabaseError(str(message or f"Supabase HTTP {response.status_code}"))
        return data

    @staticmethod
    def _session(data: dict[str, Any]) -> AuthSession:
        user = data.get("user") or {}
        return AuthSession(
            user_id=user["id"],
            email=user.get("email", ""),
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
        )
