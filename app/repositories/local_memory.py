from __future__ import annotations

from datetime import UTC, datetime, timedelta


class LocalProfileStore:
    """Development-only profile store that is reset when the server stops."""

    def __init__(self) -> None:
        self._profiles: dict[str, dict] = {}

    def get(self, user_id: str) -> dict | None:
        profile = self._profiles.get(user_id)
        if not profile:
            return None
        if profile["expires_at"] < datetime.now(UTC):
            del self._profiles[user_id]
            return None
        return profile.copy()

    def save(self, user_id: str, facts: dict) -> dict:
        profile = self._profiles.get(user_id, {"user_id": user_id})
        profile.update(facts)
        self._touch(profile)
        self._profiles[user_id] = profile
        return profile.copy()

    def touch(self, user_id: str) -> dict | None:
        profile = self.get(user_id)
        if profile:
            self._touch(profile)
            self._profiles[user_id] = profile
        return profile

    def delete(self, user_id: str) -> None:
        self._profiles.pop(user_id, None)

    @staticmethod
    def _touch(profile: dict) -> None:
        now = datetime.now(UTC)
        profile["last_active_at"] = now
        profile["expires_at"] = now + timedelta(days=30)
