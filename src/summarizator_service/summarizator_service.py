import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

model_name = "openai/gpt-oss-120b"


NEURONET_PROVIDER_TOKEN = os.getenv("NEURONET_PROVIDER_TOKEN")
NEURONET_MODEL_NAME=os.getenv("NEURONET_MODEL_NAME")
NEURONET_PROVIDER_BASE_URL=os.getenv("NEURONET_PROVIDER_BASE_URL")

client = OpenAI(
    base_url=NEURONET_PROVIDER_BASE_URL,
    api_key=NEURONET_PROVIDER_TOKEN,
)

options = {
    "summarization": """
Суммаризируй данные тебе сообщения из чата.
Сгруппируй их по темам, как считаешь нужным. Избегай шуточных или не важных тем, игнорируй флуд.
По каждой теме кратко опиши её суть и в общих словах ход её обсуждения в чате. Если было обсуждение какого-то вопроса, напиши ответ на него, если он был в чате.
Оформи ответ в виде маркированного списка. Пиши кратко, быть может, опуская детали. Главное, чтобы было понятно о чём шло обсуждение.
Вот сообщения из чата:""",

    "summariation_v2":"""
Ты — аналитик Telegram‑переписок (шумный чат: шутки, оффтоп, несколько тем, рваный контекст).
Сделай полезную сводку того, что реально происходило в чате.

ЯЗЫК:
- Ответ всегда на русском.

ФОРМАТ ВЫВОДА:
- Выводи Markdown (обычный Markdown для чтения).
- Не используй HTML-теги.
- Не используй таблицы (ни Markdown-таблицы, ни ASCII) и символ “|” для разметки.
- Не выводи “пустые” разделы: если по разделу нет данных — не пиши его вообще.
- Не вставляй строки-заглушки (“...”, “пример”, “позиция A/B”) — пиши только факты из переписки.

СМЫСЛОВЫЕ ПРАВИЛА:
- Ничего не выдумывай. Нет явного подтверждения — формулируй как “неясно/нужно уточнить”.
- Игнорируй флуд/шутки/оффтоп, если они не влияют на факты, решения, сроки, требования, риски, ошибки, ссылки и договоренности.
- Каждый пункт, который является фактом/решением/задачей/риском/советом/вопросом, ОБЯЗАН иметь Evidence.
- Evidence — список msg_id (и link, если есть).
  Если link есть, делай так: Evidence: [#123](https://...), [#456](https://...)
  Если msg_id/link не предоставлены во входе: Evidence: not_provided
- Если есть противоречие — отрази обе стороны и дай evidence для каждой.

ЛИМИТ:
- До 2200 символов. Если не помещается — сжимай, но не выкидывай решения, действия, сроки и риски.

СТИЛЬ (чтобы выглядело аккуратно):
- Заголовок — одна строка.
- Разделы — через '### ' (3 решетки).
- Пункты — через '-' и строго “1 мысль = 1 пункт”.
- Теги в highlights: [ИНФО], [ПРОБЛЕМА], [РЕШЕНИЕ], [ДЕЙСТВИЕ], [РИСК], [СОВЕТ], [ВОПРОС], [РАЗНОГЛАСИЕ].

ФОРМАТ ОТВЕТА (разделы опциональны; пустые пропускай):

{ЗАГОЛОВОК}

### Саммари
Короткий связный текст 4–10 предложений: что обсуждали, почему, что стало ясно, что осталось неясным.

### Ключевое
- [ТЕГ] одна мысль в 1 строку. Evidence: ...
- [ТЕГ] одна мысль в 1 строку. Evidence: ...
(4–10 пунктов)

### Что сделать
- действие; кто=...; срок=...; статус=todo|in_progress|done|unknown. Evidence: ...
(Пиши только если реально были поручения/планы)

### Что уточнить
- вопрос в 1 строку. Evidence: ...
(Пиши только если реально остались вопросы)

### Навигация
- тема — "точная фраза 1", "точная фраза 2". Evidence: ...
(1–4 строки максимум; только если реально помогает искать)
"""
}

class SummarizationService:
    """Асинхронный сервис для суммаризации сообщений через LLM"""

    def __init__(self, model: str = NEURONET_MODEL_NAME):
        self.model = model

    async def summarize(self, messages: list[str]) -> str | None:
        """
        Асинхронно делает суммаризацию списка сообщений.
        """
        prompt = options['summarization']
        prompt += "\n".join(messages)

        completion = await client.chat.completions.acreate(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        return completion.choices[0].message.content
    
    async def summarize_v2(self, messages: list[str]) -> str | None:
        system_prompt = options['summariation_v2']

        user_prompt = '\n'.join(messages)

        completion = await client.chat.completions.acreate(
            model=self.model,
            messages=[
                {
                    'role': 'system',
                    "content": system_prompt
                },
                {
                    'role': 'user',
                    'conent': user_prompt
                }
            ],
        )

        return completion.choices[0].message.content
