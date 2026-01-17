import os
from openai import OpenAI

model_name = "openai/gpt-oss-120b"

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)

def summarize(messages: list[str]) -> str | None:
    # with open("./prompts/summ_prompt.txt", "r", encoding="utf8") as f:
        # prompt = f.read()
    prompt = """Суммаризируй данные тебе сообщения из чата.
Сгруппируй их по темам, как считаешь нужным. Избегай шуточных или не важных тем, игнорируй флуд.
По каждой теме кратко опиши её суть и в общих словах ход её обсуждения в чате. Если было обсуждение какого-то вопроса, напиши ответ на него, если он был в чате.
Оформи ответ в виде маркированного списка. Пиши кратко, быть может, опуская детали. Главное, чтобы было понятно о чём шло обсуждение.
Вот сообщения из чата:
"""
    prompt += '\n'.join(messages)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
    )
    return completion.choices[0].message.content

