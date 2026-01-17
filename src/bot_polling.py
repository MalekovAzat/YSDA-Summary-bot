import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated
from dotenv import load_dotenv
from database.database import AsyncSessionLocal
from sqlalchemy.future import select
from aiogram.types import BotCommand
import re
import os

load_dotenv()

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("DATABASE_URL is not set in environment variables")

bot = Bot(token=BOT_TOKEN)
bot_info = None
dp = Dispatcher()

@dp.message(Command('start'))
async def start_command_handler(message: types.Message):
    await set_bot_commands(bot)
    await message.answer('Привет как дела?')

@dp.my_chat_member()
async def on_bot_added_to_chat(update: ChatMemberUpdated):
    chat_id = update.chat.id
    chat = update.chat
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status


    if old_status in ["left", "kicked"] and new_status == "member":
        async with AsyncSessionLocal() as db:
            from src.database.models.chat import Chat

            result = await db.execute(select(Chat).where(Chat.id == chat.id))
            chat_obj = result.scalar_one_or_none()

            if not chat_obj:
                chat_obj = Chat(
                    id=chat.id,
                    title=chat.title or "Без названия",
                    is_admin=False,
                    type=chat.type
                )
                db.add(chat_obj)
            await db.commit()
            await db.refresh(chat_obj)

        await bot.send_message(chat_id, "Привет! Спасибо, что добавили меня в чат! Мне нужны права администратора для того чтобы я мог получать сообщения")

    elif old_status == "member" and new_status == "administrator":
        async with AsyncSessionLocal() as db:
            from src.database.models.chat import Chat
            result = await db.execute(select(Chat).where(Chat.id == chat.id))
            chat_obj = result.scalar_one_or_none()

            chat_obj.is_admin = True

            await db.commit()
            await db.refresh(chat_obj)
            
        await bot.send_message(chat_id, "Отлично, теперь я администратор и могу получать сообщения")

    elif old_status in ['administrator'] and new_status in ['kicked', 'member'] :
        async with AsyncSessionLocal() as db:
            from src.database.models.chat import Chat
            result = await db.execute(select(Chat).where(Chat.id == chat.id))
            chat_obj = result.scalar_one_or_none()

            chat_obj.is_admin = False

            await db.commit()
            await db.refresh(chat_obj)

@dp.message(F.chat.type == "supergroup", ~F.text.startswith("/"))
async def handle_any_message(message: types.Message):
    my_text = message.text or message.caption or ""
    chat_id = message.chat.id
    message_id = message.message_id
    from_id = message.from_user.id


    internal_id = str(chat_id)[4:]
    message_link = f'https://t.me/c/{internal_id}/{message_id}'


    async with AsyncSessionLocal() as db:
        from src.database.models.message import Message
        chat_message = Message(
            id=message_id,
            chat_id=chat_id,
            from_id=from_id,
            text=my_text,
            link_in_chat=message_link
        )
        db.add(chat_message)
        await db.commit()

@dp.message(Command(commands=["summ"]), F.chat.type == "supergroup")
async def handle_summ_command(message: types.Message):
    chat_id = message.chat.id

    date_str = message.text.split(' ')[-1]
    date_regex = r"\b\d{2}-\d{2}-\d{2}\b"

    if not re.fullmatch(date_regex, date_str):
        await message.reply(f'Формат даты должен быть YY-MM-DD')
        return

    from datetime import datetime, timedelta
    date_obj = datetime.strptime(date_str, "%y-%m-%d")
    next_day = date_obj + timedelta(days=1)

    async with AsyncSessionLocal() as db:
        from src.database.models.message import Message
        from sqlalchemy import select

        result = await db.execute(
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.created_at >= date_obj,
                Message.created_at < next_day
            )
            .order_by(Message.created_at.asc())
        )
        messages = result.scalars().all()

        if not messages:
            await message.reply(f"Сообщений за эту дату нет., {date_obj, next_day}")
            return

        reply_text = "\n".join(f"{m.created_at.strftime('%d.%m.%Y %H:%M')}: {m.text}" for m in messages[-10:])
        await message.reply(reply_text)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Получить список команд"),
        BotCommand(command="summ", description="За день /summ 2025-15-10"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands(bot)
    bot_info = await bot.get_me()
    print('-- Start polling --')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())