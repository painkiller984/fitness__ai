from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Supports both `uv run python -m app.bot` and direct `uv run app/bot.py` execution.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nicegui import app, ui

from app.config import settings
from app.ui.nicegui import configure_pages


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "supabase": "configured" if settings.supabase_enabled else "demo",
        "ai": f"{settings.ai_provider}:{settings.ai_model}" if settings.ai_enabled else "deterministic",
    }


configure_pages(settings)


def run() -> None:
    settings.validate_production()
    try:
        ui.run(
            host=settings.host,
            port=settings.port,
            title=settings.app_name,
            favicon="🏃",
            storage_secret=settings.storage_secret,
            reload=False,
            show=False,
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Ctrl+C is an expected local shutdown, not an application error.
        return


if __name__ in {"__main__", "__mp_main__"}:
    run()
