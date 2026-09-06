# tech.md — Конструктор AI-ассистентов для Telegram-ботов

**v1** — первая версия документа.

## 1. Проект

Веб-панель, в которой заполняется карточка ассистента (имя, должность, язык, тон,
описание бизнеса, рабочая инструкция, сообщение при отсутствии ответа, telegram
chat id админа, токен бота). После сохранения карточки бот в Telegram отвечает
клиентам от лица этого ассистента, используя LLM. Если вопрос нестандартный или
клиент просит человека, бот отправляет сообщение об этом в чат админа и отвечает
клиенту заготовленной fallback-фразой.

Назначение: демонстрация клиентам (например, владельцу мебельного бизнеса), как
такой ассистент будет вести диалог именно в их нише, без написания кода под
каждого клиента — только заполнение формы.

Работает один человек, роль тимлида и разработчика совмещена. Документ ниже —
единственный источник правды по проекту.

## 2. Стек

- Frontend: SvelteKit (веб-панель)
- Backend: FastAPI + Uvicorn
- Валидация: Pydantic
- ORM: SQLAlchemy
- Миграции: Alembic
- БД: SQLite
- Пакетный менеджер Python: uv
- Логи: loguru
- Разворачивание: Docker / docker-compose
- Telegram: HTTP-запросы к Bot API через httpx (без сторонних telegram-фреймворков)
- LLM: DeepSeek API (OpenAI-совместимый `chat/completions` эндпоинт, `response_format: json_object`),
  вызывается через httpx, провайдер вынесен за интерфейс `services/llm.py`,
  чтобы при необходимости заменить на другой

## 3. Структура папок

```
backend/
  app/
    main.py              # создание FastAPI-приложения, роутеры, логирование
    config.py            # настройки из .env (pydantic-settings)
    database.py           # engine, session, Base
    models.py             # SQLAlchemy-модели
    schemas.py             # Pydantic-схемы (request/response)
    crud.py                 # операции с БД для ассистентов и диалогов
    routers/
      assistants.py       # CRUD + активация бота
      webhook.py           # приём апдейтов от Telegram
    services/
      telegram.py          # sendMessage, setWebhook, deleteWebhook
      llm.py                # формирование system prompt, вызов DeepSeek, парсинг ответа
    logging_conf.py       # настройка loguru
  alembic/
    versions/
    env.py
  alembic.ini
  pyproject.toml
  Dockerfile
frontend/
  src/
    routes/
      +page.svelte              # список ассистентов
      assistants/
        new/+page.svelte        # форма создания
        [id]/+page.svelte       # форма редактирования + кнопка активации
    lib/
      api.ts                    # обёртка над fetch к backend
      types.ts                  # типы, зеркалящие Pydantic-схемы
  package.json
  Dockerfile
docker-compose.yml
.env.example
tech.md
CLAUDE.md
```

## 4. Схема БД

### assistants
| поле | тип | описание |
|---|---|---|
| id | int, pk | |
| name | str | имя сотрудника |
| position | str | должность |
| language | str | язык ответов |
| tone | str | тон общения |
| business_description | text | описание бизнеса |
| work_instruction | text | рабочая инструкция |
| fallback_message | text | сообщение при отсутствии ответа |
| admin_chat_id | str | telegram chat id админа |
| bot_token | str | токен telegram-бота этого ассистента |
| webhook_active | bool, default false | зарегистрирован ли webhook |
| created_at | datetime | |
| updated_at | datetime | |

### conversations
| поле | тип | описание |
|---|---|---|
| id | int, pk | |
| assistant_id | int, fk -> assistants.id | |
| telegram_chat_id | str | chat id клиента в telegram |
| created_at | datetime | |

Уникальный индекс на (assistant_id, telegram_chat_id).

### messages
| поле | тип | описание |
|---|---|---|
| id | int, pk | |
| conversation_id | int, fk -> conversations.id | |
| role | str, enum(user, assistant) | |
| content | text | |
| created_at | datetime | |

## 5. API

- `GET /api/health` — проверка живости backend, отдаёт `{"status": "ok"}`
- `GET /api/assistants` — список ассистентов
- `POST /api/assistants` — создать ассистента
- `GET /api/assistants/{id}` — получить ассистента
- `PUT /api/assistants/{id}` — обновить ассистента
- `DELETE /api/assistants/{id}` — удалить ассистента
- `POST /api/assistants/{id}/activate` — вызвать Telegram `setWebhook` на
  `{PUBLIC_BASE_URL}/webhook/telegram/{id}`, выставить `webhook_active = true`
- `POST /api/assistants/{id}/deactivate` — вызвать `deleteWebhook`, `webhook_active = false`
- `POST /webhook/telegram/{id}` — приём апдейтов от Telegram для конкретного ассистента.
  Всегда отвечает `200 {"ok": true}`, кроме несуществующего `id` (404): на любой
  не-2xx ответ Telegram повторяет апдейт, поэтому ошибки отправки и LLM пишутся
  в лог, а не отдаются наружу. Апдейты без текстового сообщения игнорируются.
- `GET /api/assistants/{id}/conversations/{telegram_chat_id}/messages` — история
  диалога (этап 4, для просмотра демо-переписки в панели)

`activate` и `deactivate` возвращают `AssistantOut`. Если Telegram отклонил вызов
или недоступен, оба отдают `502` с описанием ошибки, `webhook_active` не меняется.

Схемы, не относящиеся к панели: `LlmReply` (ответ LLM, раздел 6) и `TelegramUpdate`
с вложенными `TelegramMessage`, `TelegramChat` (разбор апдейта, только поля
`message.chat.id` и `message.text`) лежат там же, в `schemas.py`.

Панель работает на отдельном origin, поэтому backend включает CORS-middleware
(`allow_origins=["*"]`) для запросов из браузера.

Pydantic-схемы: `AssistantCreate`, `AssistantUpdate`, `AssistantOut` — поля один в
один со схемой `assistants` (без `bot_token` в `AssistantOut`, отдавать наружу
не нужно).

## 6. Логика бота

1. Telegram присылает апдейт на `/webhook/telegram/{id}`.
2. Найти или создать `conversation` по `(assistant_id, telegram_chat_id)`.
3. Сохранить входящее сообщение в `messages` с ролью `user`.
4. Загрузить последние 10 сообщений диалога для контекста.
5. Собрать system prompt из полей ассистента:
   - имя, должность, язык, тон, описание бизнеса, рабочая инструкция;
   - явное указание: если вопрос не по теме бизнеса, требует данных, которых нет
     в описании, либо клиент прямо просит человека — вернуть `needs_human: true`.
6. Вызвать DeepSeek `chat/completions` с `response_format: {"type": "json_object"}`
   и системной инструкцией ответить строго JSON вида:
   ```json
   {"reply": "текст ответа клиенту", "needs_human": false, "reason": null}
   ```
7. Распарсить ответ через Pydantic-модель `LlmReply`. `response_format: json_object`
   гарантирует валидный JSON, но не гарантирует нужные поля — если парсинг через
   Pydantic не удался, один повтор запроса с уточнением формата, при повторной
   неудаче —
   `needs_human = true`, `reply = fallback_message`.
8. Если `needs_human = false` — отправить `reply` клиенту, сохранить как
   сообщение с ролью `assistant`.
9. Если `needs_human = true` — отправить клиенту `fallback_message` ассистента,
   отправить админу на `admin_chat_id` сообщение с именем ассистента, chat id
   клиента, последним вопросом клиента и `reason`.

## 7. Экраны панели

- Список ассистентов: имя, должность, статус (`webhook_active`), кнопки
  «Редактировать» и «Удалить», кнопка «Создать ассистента».
- Форма создания/редактирования (поля ровно как в разделе 4, без служебных):
  имя сотрудника, должность, язык, тон, описание бизнеса, рабочая инструкция,
  сообщение при отсутствии ответа, telegram chat id админа, токен бота.
- Кнопка «Активировать бота» на странице редактирования — вызывает
  `POST /api/assistants/{id}/activate`, показывает статус webhook.

## 8. Конфиг

`.env.example`:
```
DATABASE_URL=sqlite:///./data/app.db
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
PUBLIC_BASE_URL=https://example.com
LOG_LEVEL=INFO
```

`bot_token` хранится в БД (у каждого ассистента свой бот), не в `.env`.

## 9. Docker

`docker-compose.yml` поднимает два сервиса: `backend` (uvicorn, том под
sqlite-файл в `./data`) и `frontend` (сборка SvelteKit, adapter-node). Для
локальной демонстрации `PUBLIC_BASE_URL` должен быть публично доступен
(например через тестовый VPS или туннель), иначе Telegram не сможет достучаться
до `/webhook/telegram/{id}`.

## 10. Правила кода и коммитов

- Код и комментарии — на английском, интерфейс панели — на языке, заданном для
  ассистента (не путать с языком кода).
- Формат коммита: Conventional Commits, `type(scope): summary`,
  `type` из `feat|fix|refactor|chore|docs`, summary в императиве, до ~50 символов.
- Коммитить небольшими логическими шагами по ходу работы, не одним коммитом в
  конце.
- Комментарии объясняют «почему», не пересказывают код. Закомментированный код
  не оставлять.
- Активный залог, без em dash, без вводных фраз и филлеров.

## 11. Definition of Done

- Приложение поднимается `docker-compose up` без ручных правок.
- Линт и тайпчек (`ruff`/`mypy` для backend, `svelte-check` для frontend)
  проходят без ошибок.
- Миграция Alembic применяется на чистой БД.
- Ручной сценарий проходит: создать ассистента → активировать → написать боту
  обычный вопрос → получить ответ → задать вопрос не по теме → админ получает
  уведомление, клиент получает fallback-сообщение.

## 12. Дорожная карта

**Этап 0. Скелет**
Репозиторий, структура папок, `docker-compose.yml`, `.env.example`,
инициализация Alembic, пустой FastAPI-каркас, пустой SvelteKit-каркас.

**Этап 1. Backend MVP**
Модели, первая миграция, CRUD `/api/assistants`, Pydantic-схемы, loguru.

**Этап 2. Telegram + LLM**
`services/telegram.py` (sendMessage, setWebhook, deleteWebhook),
`services/llm.py` (system prompt, вызов DeepSeek, парсинг `LlmReply`),
`routers/webhook.py`, логика fallback из раздела 6, сохранение истории.

**Этап 3. Frontend MVP**
Список ассистентов, форма создания/редактирования с полями из раздела 7,
кнопка активации, удаление.

**Этап 4. По желанию**
Просмотр истории диалогов в панели, копирование итогового system prompt,
базовые тесты (`pytest` на CRUD и на сборку system prompt).
