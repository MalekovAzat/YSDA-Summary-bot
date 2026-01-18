# [std::pudge] Chat Thread Summarizer

Telegram-бот для учебных чатов: сохраняет сообщения в Postgres и по команде выдаёт **структурированное summary** обсуждения с помощью LLM. Цель – быстро понять контекст длинной переписки по ДЗ/проекту без чтения сотен сообщений.

## Возможности

* Сохраняет сообщения из supergroup в Postgres (текст, автор, время, permalink).
* Генерирует сводку за день: `/summ YY-MM-DD`.
* Генерирует сводку за период: **последний час**, **три часа**, **сегодня**, **вчера** или **неделю**.
* Личный режим: можно привязать чат по `chat_id` и получать сводку по чату в личных сообщениях с ботом.

## Команды

**В supergroup**

* `/start`, `/help` — справка
* `/chat_id` — показать ID чата
* `/summ YY-MM-DD` — summary за дату (пример: `/summ 26-01-18`)
* `/summ_1h` – суммаризация за последний час
* `/summ_3h` – суммаризация за последние 3 часа
* `/summ_todat` – суммаризация за сегодня
* `/summ_yesterday` – суммаризация за вчера
* `/summ_week` – суммаризация за неделю

**В личке**

* `/start`, `/help` — справка
* отправить `chat_id` — привязать чат
* `/summ` — выбрать чат

## Быстрый старт (Docker + Postgres)

### 1) `.env`

Создайте `.env` в корне:

```env
TG_BOT_TOKEN=123456:ABCDEF...

DATABASE_URL=postgresql+asyncpg://aib_user:aib_password@postgres:5432/aib_db

NEURONET_PROVIDER_BASE_URL=https://<openai-compatible-host>/v1
NEURONET_PROVIDER_TOKEN=<api_key>
NEURONET_MODEL_NAME=<model_name>
```

### 2) Запуск

```bash
docker compose -f docker/docker-compose-dev.yml up --build
```

### 3) Миграции

```bash
docker exec -it summary-bot alembic upgrade head
```

### 4) Проверка

Добавьте бота в чат курса, выдайте права админа, напишите пару сообщений и вызовите:

```text
/summ 26-01-18
```

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python src/bot_polling.py
```
