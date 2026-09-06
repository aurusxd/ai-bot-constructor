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
- Telegram: long polling `getUpdates` через httpx (без сторонних telegram-фреймворков).
  Polling выбран вместо webhook, чтобы не требовать HTTPS и публичного адреса:
  бот сам ходит за апдейтами и работает с любой машины, в том числе локальной
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
      assistants.py       # CRUD + запуск и остановка бота
    services/
      telegram.py          # sendMessage, getUpdates, deleteWebhook
      llm.py                # формирование system prompt, вызов DeepSeek, парсинг ответа
      dialog.py             # обработка одного входящего сообщения (раздел 6)
      poller.py             # поток long polling на каждого активного ассистента
    logging_conf.py       # настройка loguru
  alembic/
    versions/
    env.py
  tests/
    conftest.py           # тестовое приложение на отдельной БД
    test_crud.py          # CRUD ассистентов и диалогов
    test_llm.py           # сборка system prompt и разбор ответа LLM
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
      AssistantForm.svelte      # общая форма создания и редактирования
      Conversations.svelte      # список диалогов и переписка выбранного чата
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
| bot_active | bool, default false | запущен ли polling для этого бота |
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
- `POST /api/assistants/{id}/activate` — запустить polling для бота ассистента,
  выставить `bot_active = true`
- `POST /api/assistants/{id}/deactivate` — остановить polling, `bot_active = false`
- `GET /api/assistants/{id}/conversations` — список диалогов ассистента, новые
  сверху, схема `ConversationOut` (`id`, `telegram_chat_id`, `created_at`)
- `GET /api/assistants/{id}/conversations/{telegram_chat_id}/messages` — история
  диалога в хронологическом порядке, схема `MessageOut` (`id`, `role`, `content`,
  `created_at`). `404`, если у ассистента нет диалога с таким chat id
- `GET /api/assistants/{id}/system-prompt` — итоговый system prompt ассистента,
  тот же текст, что уходит в LLM, схема `SystemPromptOut` (`prompt`). Нужен,
  чтобы скопировать его из панели и проверить на стороне

`activate` и `deactivate` возвращают `AssistantOut`. `activate` перед запуском
проверяет токен вызовом `getMe` и снимает возможный webhook через `deleteWebhook`:
Telegram не отдаёт `getUpdates`, пока у бота зарегистрирован webhook. Если токен
отклонён или Telegram недоступен, `activate` отдаёт `502`, `bot_active` не меняется
и поток не стартует.

Схемы, не относящиеся к панели: `LlmReply` (ответ LLM, раздел 6) и `TelegramUpdate`
с вложенными `TelegramMessage`, `TelegramChat` (разбор апдейта, только поля
`message.chat.id` и `message.text`) лежат там же, в `schemas.py`.

Панель работает на отдельном origin, поэтому backend включает CORS-middleware
(`allow_origins=["*"]`) для запросов из браузера.

Pydantic-схемы: `AssistantCreate`, `AssistantUpdate`, `AssistantOut` — поля один в
один со схемой `assistants` (без `bot_token` в `AssistantOut`, отдавать наружу
не нужно). В `AssistantUpdate` поле `bot_token` необязательное: панель не может
показать текущий токен в форме, поэтому пустое значение означает «оставить
сохранённый токен», а непустое — заменить его.

## 6. Логика бота

1. Поток поллера ассистента получает апдейт из `getUpdates` и берёт из него
   текстовое сообщение. Апдейты без текста пропускаются.
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

Поллинг: на каждого активного ассистента поднимается отдельный поток, который в
цикле вызывает `getUpdates` с `timeout=25` и `offset = последний update_id + 1`.
Ошибки сети и Telegram логируются, поток засыпает на несколько секунд и повторяет,
чтобы временная недоступность не гасила бота. Offset хранится в памяти потока:
после перезапуска backend Telegram отдаёт неподтверждённые апдейты за последние
24 часа, поэтому возможен повторный ответ на последнее сообщение. Обработка
сообщений внутри одного бота последовательная — ответы в диалоге не обгоняют
друг друга.

Потоки поднимаются при старте приложения для всех ассистентов с `bot_active = true`
и останавливаются при завершении работы.

## 7. Экраны панели

- Список ассистентов: имя, должность, статус (`bot_active`), кнопки
  «Редактировать» и «Удалить», кнопка «Создать ассистента».
- Форма создания/редактирования (поля ровно как в разделе 4, без служебных):
  имя сотрудника, должность, язык, тон, описание бизнеса, рабочая инструкция,
  сообщение при отсутствии ответа, telegram chat id админа, токен бота.
- Кнопка «Активировать бота» на странице редактирования — вызывает
  `POST /api/assistants/{id}/activate`, показывает статус бота.
- На той же странице: блок «Диалоги» со списком чатов и перепиской выбранного
  чата, и кнопка «Скопировать system prompt», кладущая текст в буфер обмена.
  Буфер обмена доступен только в secure context (https или localhost), поэтому
  при отказе панель показывает промпт в поле для ручного копирования.

## 8. Конфиг

`.env.example`:
```
DATABASE_URL=sqlite:///./data/app.db
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
LOG_LEVEL=INFO
PUBLIC_API_BASE_URL=http://localhost:8010
```

`PUBLIC_API_BASE_URL` читает frontend: это адрес backend, по которому к нему
обращается браузер, а не адрес внутри docker-сети. Префикс `PUBLIC_` требует
SvelteKit для переменных, доступных в браузере.

`bot_token` и `admin_chat_id` в `.env` не выносятся: они свои у каждого
ассистента (свой бот и свой админ) и хранятся в таблице `assistants`,
заполняются через форму панели. В `.env` только общие для всей установки
настройки.

## 9. Docker

`docker-compose.yml` поднимает два сервиса: `backend` (uvicorn, том под
sqlite-файл в `./data`) и `frontend` (сборка SvelteKit, adapter-node). Публичный
адрес не нужен: бот сам ходит в Telegram за апдейтами, поэтому стек одинаково
работает на VPS и на локальной машине, достаточно исходящего доступа в интернет.

Наружу публикуются порты `8010` для backend и `3000` для frontend; внутри
контейнера backend слушает `8000`. При смене публикуемого порта backend нужно
поправить и `PUBLIC_API_BASE_URL`, иначе панель будет стучаться не туда.

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
- После перезапуска стека боты активных ассистентов поднимаются сами.

## 12. Дорожная карта

**Этап 0. Скелет**
Репозиторий, структура папок, `docker-compose.yml`, `.env.example`,
инициализация Alembic, пустой FastAPI-каркас, пустой SvelteKit-каркас.

**Этап 1. Backend MVP**
Модели, первая миграция, CRUD `/api/assistants`, Pydantic-схемы, loguru.

**Этап 2. Telegram + LLM**
`services/telegram.py` (sendMessage, getUpdates, deleteWebhook),
`services/llm.py` (system prompt, вызов DeepSeek, парсинг `LlmReply`),
`services/dialog.py` и `services/poller.py`, логика fallback из раздела 6,
сохранение истории.

**Этап 3. Frontend MVP**
Список ассистентов, форма создания/редактирования с полями из раздела 7,
кнопка активации, удаление.

**Этап 4. По желанию**
Просмотр истории диалогов в панели, копирование итогового system prompt,
базовые тесты (`pytest` на CRUD и на сборку system prompt).
