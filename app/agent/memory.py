from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversationMemory:
    """Short-lived per-session memory; persistent history belongs in Supabase later."""

    messages: list[dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def recent(self, limit: int = 6) -> list[dict[str, str]]:
        return self.messages[-limit:]
