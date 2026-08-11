from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from nicegui import app, ui

from app.agent.memory import ConversationMemory
from app.agent.language import response_language
from app.agent.chat_policy import (
    build_complete_profile,
    format_profile_data,
    public_profile_context,
    should_use_bounded_agent,
    target_facts,
)
from app.agent.orchestrator import FitnessAgent
from app.agent.onboarding import current_onboarding_stage, onboarding_context, onboarding_reply
from app.agent.profile_facts import extract_durable_dietary_preferences, extract_profile_facts, is_valid_profile_name
from app.agent.router import route_intent
from app.config import Settings
from app.guards.safety import urgent_message_if_needed
from app.knowledge.rag import FitnessKnowledgeRetriever
from app.providers.factory import create_provider_bundle
from app.repositories.local_memory import LocalProfileStore
from app.repositories.supabase import SupabaseError, SupabaseGateway
from app.tools.calorie_macros import calculate_nutrition_targets
from app.tools.menu_templates import (
    build_daily_menu,
    build_menu_with_found_food,
    is_known_food,
    requested_portion_grams,
)
from app.tools.workout_program import build_workout_program


def configure_pages(settings: Settings) -> None:
    provider = create_provider_bundle(settings)
    bounded_agent = FitnessAgent(provider.generator, provider.judge, FitnessKnowledgeRetriever())
    gateway = (
        SupabaseGateway(settings.supabase_url, settings.supabase_publishable_key)
        if settings.supabase_enabled
        else None
    )
    local_profiles = LocalProfileStore()

    @ui.page("/")
    async def index() -> None:
        ui.add_head_html(
            """
            <style>
              :root { color-scheme: dark; }
              body, .q-page { background: #0b0d10; color: #f8fafc; }
              .chat-shell { height: 100vh; max-width: 920px; margin: 0 auto; }
              .topbar { background: rgba(11,13,16,.94); border-bottom: 1px solid #282e37; }
              .brand-mark { background: #f4f4f5; color: #111318; border-radius: 9px; padding: 5px 8px; font-weight: 800; }
              .composer { background: #171c23; border: 1px solid #353d48; border-radius: 18px; }
              .composer .q-field__control, .composer textarea { background: transparent !important; color: #fff !important; }
              .composer textarea::placeholder { color: #9ca7b5 !important; opacity: 1; }
              .assistant-bubble, .user-bubble { display: inline-block; height: auto !important; min-height: 0 !important; background: #20262e; color: #fff; border: 1px solid #353d48; border-radius: 16px; padding: 12px 15px; max-width: min(760px, 90%); animation: message-in .22s ease-out; }
              .user-bubble { background: #2a303a; }
              .assistant-bubble .q-markdown, .user-bubble .q-markdown { margin: 0 !important; padding: 0 !important; min-height: 0 !important; }
              .assistant-bubble p, .user-bubble p, .assistant-bubble .q-markdown p, .user-bubble .q-markdown p { color: #fff !important; margin: 0 !important; padding: 0 !important; }
              .typing { color: #b8c2d0; font-size: .9rem; animation: pulse 1.1s ease-in-out infinite; }
              .prompt-chip { background: rgba(116, 126, 141, .24) !important; border: 1px solid rgba(180, 191, 207, .25); border-radius: 13px; color: #eef2f7 !important; }
              .prompt-chip .q-btn__content { color: #eef2f7 !important; }
              .send-button { width: 44px; height: 44px; min-width: 44px; padding: 0 !important; background: #f4f4f5 !important; color: #111318 !important; border: 1px solid #fff; }
              .send-button .q-btn__content, .send-button .q-icon { color: #111318 !important; }
              .new-chat-button, .new-chat-button .q-btn__content, .new-chat-button .q-icon { color: #f4f4f5 !important; }
              .desktop-actions { display: flex !important; }
              .mobile-actions { display: none !important; }
              .action-menu { min-width: 220px; padding: 6px; background: #20262e !important; color: #f4f4f5 !important; border: 1px solid #3a424e; border-radius: 12px; box-shadow: 0 14px 38px rgba(0,0,0,.45); }
              .action-menu .q-item { min-height: 42px; color: #f4f4f5 !important; border-radius: 8px; }
              .action-menu .q-item:hover { background: rgba(255,255,255,.08) !important; }
              .action-menu .danger-action { color: #ff9c9c !important; }
              @media (max-width: 767px) {
                .desktop-actions { display: none !important; }
                .mobile-actions { display: flex !important; }
              }
              @keyframes message-in { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
              @keyframes pulse { 50% { opacity: .42; } }
            </style>
            """
        )
        state: dict[str, Any] = {
            "memory": ConversationMemory(),
            "profile": None,
            "pending_facts": {},
            "active_workflow": None,
            "workout_setup": None,
            "token": None,
            "user_id": None,
        }

        def activate_local_fallback(seed: dict[str, Any] | None = None) -> None:
            user_id = app.storage.user.get("local_profile_id") or str(uuid4())
            app.storage.user["local_profile_id"] = user_id
            state["token"], state["user_id"] = None, user_id
            state["profile"] = (
                local_profiles.save(user_id, public_profile_context(seed))
                if seed
                else local_profiles.get(user_id)
            )

        if gateway:
            try:
                token = app.storage.user.get("anonymous_access_token")
                user_id = app.storage.user.get("anonymous_user_id")
                if not token or not user_id:
                    session = await gateway.sign_in_anonymously()
                    token, user_id = session.access_token, session.user_id
                    app.storage.user.update(
                        anonymous_access_token=token,
                        anonymous_refresh_token=session.refresh_token,
                        anonymous_user_id=user_id,
                    )
                try:
                    state["profile"] = await gateway.get_anonymous_profile(token, user_id)
                except SupabaseError:
                    session = await gateway.refresh_session(app.storage.user.get("anonymous_refresh_token", ""))
                    token, user_id = session.access_token, session.user_id
                    app.storage.user.update(
                        anonymous_access_token=token,
                        anonymous_refresh_token=session.refresh_token,
                        anonymous_user_id=user_id,
                    )
                    state["profile"] = await gateway.get_anonymous_profile(token, user_id)
                state["token"], state["user_id"] = token, user_id
            except SupabaseError:
                activate_local_fallback()
        else:
            user_id = app.storage.user.get("local_profile_id")
            if not user_id:
                user_id = str(uuid4())
                app.storage.user["local_profile_id"] = user_id
            state["user_id"] = user_id
            state["profile"] = local_profiles.get(user_id)

        # Repair values written by older compact-profile parsing logic, which could
        # mistake a goal such as "похудение" for the user's name.
        if state["profile"] and state["profile"].get("name") and not is_valid_profile_name(state["profile"]["name"]):
            if gateway and state["token"]:
                try:
                    state["profile"] = await gateway.save_anonymous_facts(
                        state["token"], state["user_id"], {"name": None}
                    )
                except SupabaseError:
                    activate_local_fallback({**state["profile"], "name": None})
            else:
                state["profile"] = local_profiles.save(state["user_id"], {"name": None})

        with ui.column().classes("chat-shell w-full no-wrap"):
            with ui.row().classes("topbar w-full items-center justify-between px-4 py-3"):
                with ui.row().classes("items-center gap-3"):
                    ui.label("F").classes("brand-mark")
                    with ui.column().classes("gap-0"):
                        ui.label("Forma").classes("text-base font-bold text-white")
                        ui.label("Фитнес-тренер и нутрициолог").classes("text-xs text-gray-400")

            chat_scroll = ui.scroll_area().classes("w-full grow px-3 md:px-6")
            with chat_scroll:
                chat = ui.column().classes("w-full gap-4 py-8")

            with ui.column().classes("w-full px-3 md:px-6 pb-5"):
                quick_actions = (
                    "Рассчитать калории",
                    "Составить тренировку",
                    "Подобрать меню",
                    "Покажи мои данные",
                    "Удалить мои данные",
                )
                with ui.row().classes("desktop-actions w-full justify-center gap-2 pb-3 flex-wrap"):
                    quick_buttons = [
                        ui.button(text, on_click=lambda value=text: ask(value))
                        .props("flat dense no-caps")
                        .classes("prompt-chip text-xs")
                        .style("background: rgba(116, 126, 141, .24) !important; color: #eef2f7 !important;")
                        for text in quick_actions
                    ]
                with ui.row().classes("mobile-actions w-full justify-center pb-3"):
                    with ui.button("Действия", icon="more_horiz").props("flat dense no-caps").classes("prompt-chip"):
                        with ui.menu().classes("action-menu"):
                            for text in quick_actions:
                                item = ui.menu_item(text, on_click=lambda value=text: ask(value))
                                if text == "Удалить мои данные":
                                    item.classes("danger-action")
                with ui.row().classes("composer w-full items-center px-3 py-1 gap-2"):
                    question = ui.textarea(placeholder="Напишите сообщение…").props("autogrow borderless").classes("grow")
                    send_button = ui.button(icon="send").props("round unelevated") \
                        .classes("send-button") \
                        .style("background: #f4f4f5 !important; color: #111318 !important;")

        async def scroll_to_latest() -> None:
            """Wait for NiceGUI to render the new message before scrolling the chat container."""
            await asyncio.sleep(0.08)
            chat_scroll.scroll_to(percent=1, duration=0.2)
            await asyncio.sleep(0.25)
            chat_scroll.scroll_to(percent=1)

        def add_bubble(text: str, sent: bool = False) -> None:
            with chat:
                with ui.row().classes(f"w-full {'justify-end' if sent else 'justify-start'}"):
                    ui.markdown(text).classes("user-bubble" if sent else "assistant-bubble")
            asyncio.create_task(scroll_to_latest())

        def add_typing() -> Any:
            with chat:
                typing = ui.row().classes("w-full justify-start items-center gap-2")
                with typing:
                    ui.spinner("dots", size="20px", color="lime-5")
                    ui.label("Forma печатает…").classes("typing")
            asyncio.create_task(scroll_to_latest())
            return typing

        async def ask(text: str | None = None) -> None:
            message = (text if text is not None else question.value).strip()
            if not message:
                return
            question.set_value("")
            question.update()
            add_bubble(message, sent=True)
            typing = add_typing()
            try:
                normalized = message.casefold().strip()
                language = response_language(message)
                intent = route_intent(message)
                if intent == "workout_plan" and state["active_workflow"] != "workout_plan":
                    state["active_workflow"] = "workout_plan"
                    # Reconfirm the safety-critical training context for each new program.
                    # Older profile values may describe a previous routine.
                    state["workout_setup"] = {
                        "training_place": None,
                        "training_experience": None,
                        "health_screened": False,
                    }
                elif intent in {"nutrition_targets", "meal_plan"}:
                    state["active_workflow"] = intent
                elif intent == "meal_adjustment":
                    state["active_workflow"] = "meal_plan"
                delete_commands = {"удали мои данные", "удалить мои данные", "delete my data"}
                show_commands = {"покажи мои данные", "показать мои данные", "show my data"}
                if normalized in delete_commands and gateway and state["token"]:
                    await gateway.request_anonymous_deletion(state["token"], state["user_id"])
                    for key in ("anonymous_access_token", "anonymous_refresh_token", "anonymous_user_id"):
                        app.storage.user.pop(key, None)
                    state["token"], state["user_id"] = None, None
                    try:
                        session = await gateway.sign_in_anonymously()
                        app.storage.user.update(
                            anonymous_access_token=session.access_token,
                            anonymous_refresh_token=session.refresh_token,
                            anonymous_user_id=session.user_id,
                        )
                        state["token"], state["user_id"] = session.access_token, session.user_id
                    except SupabaseError:
                        activate_local_fallback()
                    state["profile"] = None
                    state["memory"] = ConversationMemory()
                    state["pending_facts"] = {}
                    state["active_workflow"] = None
                    state["workout_setup"] = None
                    typing.delete()
                    add_bubble(
                        "Your data has been cleared and queued for permanent deletion. You can start again by telling me about yourself."
                        if language == "en"
                        else "Ваши данные очищены и поставлены на окончательное удаление. Можно начать заново: просто расскажите о себе."
                    )
                    return
                if normalized in delete_commands:
                    local_profiles.delete(state["user_id"])
                    state["profile"] = None
                    state["memory"] = ConversationMemory()
                    state["pending_facts"] = {}
                    state["active_workflow"] = None
                    state["workout_setup"] = None
                    typing.delete()
                    add_bubble(
                        "Your local profile has been deleted. You can start again by telling me about yourself."
                        if language == "en"
                        else "Локальный профиль удалён. При желании можно начать заново: просто расскажите о себе."
                    )
                    return
                if normalized in show_commands:
                    typing.delete()
                    add_bubble(format_profile_data(state["profile"], language))
                    return
                known_profile = {
                    **public_profile_context(state["profile"]),
                    **state["pending_facts"],
                }
                workout_setup = state["workout_setup"]
                onboarding_profile = (
                    {**known_profile, **workout_setup}
                    if state["active_workflow"] == "workout_plan" and workout_setup is not None
                    else known_profile
                )
                expected_stage = current_onboarding_stage(onboarding_profile, state["active_workflow"])
                expected_fields = set(expected_stage.missing_fields) if expected_stage else set()
                facts = extract_profile_facts(message, expected_fields)
                if state["active_workflow"] == "workout_plan" and workout_setup is not None:
                    workout_setup.update(
                        {
                            key: facts[key]
                            for key in ("training_place", "training_experience", "health_screened")
                            if key in facts
                        }
                    )
                preferences = extract_durable_dietary_preferences(message)
                if preferences:
                    saved_preferences = list(known_profile.get("dietary_preferences") or [])
                    facts["dietary_preferences"] = list(dict.fromkeys([*saved_preferences, *preferences]))
                combined_facts = {**state["pending_facts"], **facts}
                can_persist = bool(known_profile.get("name") or combined_facts.get("name"))
                if not can_persist:
                    state["pending_facts"] = combined_facts
                    facts_to_save: dict[str, Any] = {}
                else:
                    facts_to_save = combined_facts
                    state["pending_facts"] = {}
                if gateway and state["token"]:
                    try:
                        if facts_to_save:
                            state["profile"] = await gateway.save_anonymous_facts(
                                state["token"], state["user_id"], facts_to_save
                            )
                        elif state["profile"]:
                            state["profile"] = await gateway.touch_anonymous_profile(
                                state["token"], state["user_id"]
                            )
                    except SupabaseError:
                        activate_local_fallback({**(state["profile"] or {}), **facts})
                elif facts_to_save:
                    state["profile"] = local_profiles.save(state["user_id"], facts_to_save)
                elif state["profile"]:
                    state["profile"] = local_profiles.touch(state["user_id"])
                profile_context = {
                    key: value.isoformat() if isinstance(value, (date, datetime)) else value
                    for key, value in {
                        **public_profile_context(state["profile"]),
                        **state["pending_facts"],
                    }.items()
                }
                workflow_profile = (
                    {**profile_context, **workout_setup}
                    if state["active_workflow"] == "workout_plan" and workout_setup is not None
                    else profile_context
                )
                onboarding_stage = current_onboarding_stage(workflow_profile, state["active_workflow"])
                if onboarding_stage:
                    workflow_profile["_onboarding"] = onboarding_context(onboarding_stage, language)
                urgent_reply = urgent_message_if_needed(message)
                complete_profile = build_complete_profile(profile_context)
                if complete_profile:
                    targets = calculate_nutrition_targets(complete_profile)
                    updates = target_facts(targets)
                    if any(profile_context.get(key) != value for key, value in updates.items()):
                        if gateway and state["token"]:
                            state["profile"] = await gateway.save_anonymous_facts(
                                state["token"], state["user_id"], updates
                            )
                        else:
                            state["profile"] = local_profiles.save(state["user_id"], updates)
                        profile_context.update(updates)
                if urgent_reply:
                    reply = urgent_reply
                    state["memory"].add("user", message)
                    state["memory"].add("assistant", reply)
                elif onboarding_stage:
                    reply = onboarding_reply(onboarding_stage, language)
                    state["memory"].add("user", message)
                    state["memory"].add("assistant", reply)
                elif state["active_workflow"] == "workout_plan" and onboarding_stage is None:
                    grounded_workout = (
                        await provider.plan_search.workout(workflow_profile, language)
                        if provider.plan_search
                        else None
                    )
                    reply = (
                        grounded_workout.render(language)
                        if grounded_workout
                        else (
                            build_workout_program(workflow_profile, language)
                            + (
                                "\n\n⚠️ Google Search is temporarily unavailable; this is Forma's local fallback plan."
                                if language == "en"
                                else "\n\n⚠️ Google Search временно недоступен — показан локальный резервный план Forma."
                            )
                        )
                    )
                    state["active_workflow"] = None
                    state["workout_setup"] = None
                    state["memory"].add("user", message)
                    state["memory"].add("assistant", reply)
                else:
                    workflow_intent = state["active_workflow"] or intent
                    if workflow_intent == "meal_plan" and complete_profile:
                        targets = calculate_nutrition_targets(complete_profile)
                        if intent == "meal_adjustment" and not is_known_food(message) and provider.food_search:
                            found_food = await provider.food_search.lookup(message)
                            portion = requested_portion_grams(message)
                            if found_food and portion:
                                reply = build_menu_with_found_food(
                                    targets, profile_context, name=found_food.name, grams=portion,
                                    kcal_per_100g=found_food.kcal_per_100g,
                                    protein_per_100g=found_food.protein_per_100g,
                                    fat_per_100g=found_food.fat_per_100g,
                                    carbs_per_100g=found_food.carbs_per_100g,
                                    sources=found_food.sources,
                                )
                            elif found_food:
                                reply = (
                                    f"Нашёл данные для «{found_food.name}»: {found_food.kcal_per_100g:g} ккал на 100 г. "
                                    f"Напиши порцию в граммах — и я сразу внесу продукт в текущий расчёт. Источник: {found_food.sources[0]}"
                                )
                            else:
                                reply = "Не удалось надёжно найти КБЖУ этого продукта. Пришли фото или данные с упаковки — я учту их в расчёте."
                        else:
                            grounded_menu = (
                                await provider.plan_search.menu(profile_context, targets, language)
                                if provider.plan_search
                                else None
                            )
                            reply = (
                                grounded_menu.render(language)
                                if grounded_menu
                                else (
                                    build_daily_menu(targets, profile_context, language=language)
                                    + (
                                        "\n\n⚠️ Google Search is temporarily unavailable; this is Forma's local fallback menu."
                                        if language == "en"
                                        else "\n\n⚠️ Google Search временно недоступен — показано локальное резервное меню Forma."
                                    )
                                )
                            )
                        state["active_workflow"] = None
                        state["memory"].add("user", message)
                        state["memory"].add("assistant", reply)
                    elif should_use_bounded_agent(workflow_intent, complete_profile):
                        reply = (await bounded_agent.respond(complete_profile, message, state["memory"])).message
                        state["active_workflow"] = None
                    else:
                        reply = await provider.conversation.respond(
                            message, state["memory"].recent(), workflow_profile
                        )
                        state["memory"].add("user", message)
                        state["memory"].add("assistant", reply)
                typing.delete()
                add_bubble(reply)
            except Exception:
                logging.exception("Chat request failed")
                typing.delete()
                add_bubble(
                    "I couldn’t prepare a response. Please try again in a moment."
                    if response_language(message) == "en"
                    else "Не удалось подготовить ответ. Попробуйте ещё раз чуть позже."
                )

        async def ask_from_browser(event: Any) -> None:
            """Submit the value captured in the browser before clearing the textarea."""
            message = event.args if isinstance(event.args, str) else ""
            await ask(message)

        clear_and_submit = """(value, input) => {
            if (!value.trim()) return;
            input.value = '';
            input.dispatchEvent(new Event('input', {bubbles: true}));
            emit(value);
        }"""
        question.on(
            "keydown.enter",
            ask_from_browser,
            js_handler=f"""(event) => {{
                if (event.shiftKey) return;
                event.preventDefault();
                ({clear_and_submit})(event.target.value, event.target);
            }}""",
        )
        send_button.on(
            "click",
            ask_from_browser,
            js_handler=f"""() => {{
                const input = getHtmlElement({question.id})?.querySelector('textarea');
                if (input) ({clear_and_submit})(input.value, input);
            }}""",
        )
