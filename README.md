# Forma — фитнес-тренер и помощник по питанию

Первый вертикальный MVP: NiceGUI-интерфейс, FastAPI health endpoint, Supabase Auth/Data API,
детерминированный расчёт калорий и БЖУ, safety gate и опциональный Gemini generator/judge.

## Локальный запуск

```powershell
uv sync
Copy-Item .env.example .env
uv run python -m app.bot
```

Откройте `http://localhost:8080`. Без ключей приложение запускается в demo-режиме:
анкета и расчёты работают, ответы формируются детерминированно.

## Supabase

1. Создайте проект Supabase.
2. Выполните [`supabase/schema.sql`](supabase/schema.sql) в SQL Editor.
3. В Authentication → Providers включите **Anonymous Sign-Ins**.
4. Включите CAPTCHA или Cloudflare Turnstile для защиты анонимной регистрации от злоупотреблений.
5. Заполните в `.env` `SUPABASE_URL` и `SUPABASE_PUBLISHABLE_KEY` из окна Connect.
6. Не используйте `service_role`: приложение обращается к Data API с JWT пользователя, а строки
   защищены RLS.

### Анонимная память Forma

Forma создаёт анонимную сессию в защищённой cookie и хранит только явно названные поля профиля:
имя, возраст, пол, рост, вес, цель, активность и рассчитанные калории/БЖУ. Обычные сообщения и
история чата в Supabase не сохраняются.

`schema.sql` включает `pg_cron` и создаёт ежедневную задачу очистки. Она удаляет анонимные Auth-профили,
неактивные 30 дней. Команда «удали мои данные» немедленно очищает персональные поля и ставит Auth-профиль
на окончательное удаление ближайшей ежедневной задачей.

Команды в чате: «покажи мои данные», «измени вес до 80 кг», «удали мои данные».

## Смена модели и провайдера

LLM-провайдер выбирается переменными `AI_*`. Router, Tools, RAG, Guards и Judge-пайплайн при
переключении не меняются.

| Провайдер | `AI_PROVIDER` | Что задать дополнительно |
| --- | --- | --- |
| Gemini | `gemini` | `AI_API_KEY`, модель `gemini-3.5-flash-lite` |
| OpenAI | `openai` | `AI_API_KEY`, например `gpt-4.1-mini` |
| Совместимый API | `openai_compatible` | `AI_API_KEY`, `AI_BASE_URL` |
| OpenRouter / Groq / Together / DeepSeek | имя провайдера | `AI_API_KEY`, `AI_BASE_URL` |
| Ollama локально | `ollama` | `AI_MODEL`, при необходимости `AI_BASE_URL` |
| Без модели | `deterministic` | ничего |

Пример Gemini:

```env
AI_PROVIDER=gemini
AI_MODEL=gemini-3.5-flash-lite
AI_JUDGE_MODEL=gemini-3.5-flash-lite
AI_API_KEY=...
```

Пример локального Ollama:

```env
AI_PROVIDER=ollama
AI_MODEL=qwen2.5:7b
AI_JUDGE_MODEL=qwen2.5:7b
AI_BASE_URL=http://localhost:11434/v1
```

Для OpenAI-compatible провайдеров в `AI_BASE_URL` нужно указать URL, оканчивающийся на `/v1`.
Без ключа применяется `DeterministicGenerator`. Числа всегда поступают из
`calculate_nutrition_targets`, а не из модели.

`ollama` работает при локальном запуске. Render не сможет обратиться к `localhost` вашего
компьютера: для облачного деплоя используйте API-провайдера или отдельно доступный Ollama-сервер.

## Агентная логика

```text
Router → Safety Guard → Plan/Execute → Tools → RAG → Generator → Validators → Judge
```

- `app/agent` — Router, краткосрочная память, execution plan и оркестратор.
- `app/tools` — детерминированные инструменты, включая расчёт калорий и БЖУ.
- `app/guards` — safety gate и запреты для рискованных запросов.
- `app/knowledge` — retrieval по курируемой базе знаний.
- `app/providers` — Gemini Generator и локальный deterministic fallback.
- `app/judges` — отдельный Plan Judge, который допускает только один repair-проход.
- `app/repositories` — Supabase Auth/Data API.
- `app/ui` — NiceGUI-интерфейс.

## Render

Репозиторий содержит `render.yaml`. Создайте Blueprint/Web Service из репозитория и задайте
секретные переменные в Render Dashboard. Проверка состояния: `/health`.

Обязательные переменные Render:

```text
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
AI_API_KEY
```

`APP_STORAGE_SECRET` Render генерирует автоматически. Production-запуск намеренно остановится с
понятной ошибкой, если постоянное хранилище, AI-ключ или storage secret не настроены.

После первого деплоя проверьте:

1. `/health` возвращает `status: ok`, `supabase: configured` и выбранную AI-модель.
2. Первый браузер сохраняет профиль и видит его командой «покажи мои данные».
3. Инкогнито-окно не видит данные первого браузера — это проверка RLS.
4. «Рассчитать калории» возвращает значения из детерминированного инструмента.
5. «Удалить мои данные» очищает профиль; после этого команда показа не возвращает старые значения.

## Проверка

```powershell
uv run pytest -q
```

## Безопасность

- бот не ставит диагнозы и не назначает лечение;
- тревожные симптомы блокируют генерацию плана;
- беременность, несовершеннолетие и медицинские состояния направляются к специалисту;
- RLS ограничивает каждую запись владельцем `auth.uid()`;
- publishable key допустим в клиенте только вместе с RLS; service-role key не используется.
