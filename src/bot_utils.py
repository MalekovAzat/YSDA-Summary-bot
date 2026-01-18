from datetime import datetime
from src.database.models.message import Message
from aiogram import Bot, types
from aiogram.enums import ChatMemberStatus
from src.summarizator_service.summarizator_service import SummarizationService
from src.database.database import AsyncSessionLocal
from src.chat_service.chat_service import ChatService
from md2tgmd import escape

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]

def _parse_from_id(id_str: str) -> int:
    if id_str.startswith("user"):
        return int(id_str[4:])
    elif id_str.startswith("channel"):
        return int(id_str[7:])
    else:
        return -1

def convert_messages(chat_json) -> list[Message]:
    chat_id = chat_json['id']

    topic_message = next(
            filter(lambda x: x.get("action") == "topic_created", chat_json['messages']),
            None
        )
    topic_id = topic_message['id'] if topic_message else None

    res = []

    for message_json in chat_json['messages']:
        if message_json['type'] != 'message':
                continue
        
        message = Message()
        message.id = message_json['id']
        message.chat_id = int("-100" + str(chat_id))

        message.from_id = _parse_from_id(message_json["from_id"])
        message.text = ''.join([text["text"] for text in message_json["text_entities"]])
        message.created_at = datetime.strptime(message_json["date"], "%Y-%m-%dT%H:%M:%S")

        internal_id = str(message.chat_id)[4:]
        message.link_in_chat = f'https://t.me/c/{internal_id}/{topic_id}/{message.id}' if topic_id else f'https://t.me/c/{internal_id}/{message.id}'
        message.from_name = message_json["from"]

        res.append(message)
    return res

def check_if_tagged(message: types.Message, username: str) -> bool:
    if message.text is None:
        return False
    if message.entities:
        for entity in message.entities:
            if entity.type == 'mention':
                # Extract the mentioned text using offset and length
                mentioned_text = message.text[entity.offset:entity.offset + entity.length]
                # Check if the mentioned text (including '@') matches the bot's username
                if mentioned_text == f'@{username}':
                    return True
    return False

async def summarize_messages(chat_id: int, bot_id: int, date_from: datetime, date_to: datetime):
    """
    Общая функция для суммаризации сообщений за указанный период
    """
    reply: str = None
    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db)
        messages = await chat_service.get_messages_for_day(
            chat_id=chat_id, bot_id=bot_id, date_from=date_from, date_to=date_to
        )

        if not messages:
            return f"Сообщений за этот период нет ({date_from} - {date_to})"

        messages_text = [
            f"{msg.created_at.strftime('%d.%m.%Y %H:%M')} {msg.from_name} {msg.link_in_chat}: {msg.text}"
            for msg in messages
        ]

    summarizator = SummarizationService()
    try:
        result = await summarizator.summarize_v2(messages_text)
        reply = escape(result)
    except Exception as e:
        reply = "К сожалению, суммаризация завершилась с ошибкой 😕"

    return reply