import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated
from dotenv import load_dotenv
from database.database import AsyncSessionLocal
from sqlalchemy.future import select
from aiogram.types import BotCommand
from src.command_dispatcher import dp
import bot_handlers.private_chat
import bot_handlers.supergroup

load_dotenv()


BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("DATABASE_URL is not set in environment variables")

bot = Bot(token=BOT_TOKEN)

async def set_bot_commands(bot: Bot):
    group_commands = [
        BotCommand(command="start", description="🚀 Получить список команд"),
        BotCommand(command="import", description="📥 Импортирование сообщений чата"),
        BotCommand(command="chat_id", description="🆔 Получить идентификатор чата"),
        BotCommand(command="summ", description="📅 За конкретный день /summ 25-15-10"),
        BotCommand(command="summ_1h", description="⏱ За последний час"),
        BotCommand(command="summ_3h", description="🕒 За последние 3 часа"),
        BotCommand(command="summ_today", description="🌞 За сегодня"),
        BotCommand(command="summ_yesterday", description="🌙 За вчера"),
        BotCommand(command="summ_week", description="📊 За неделю"),
    ]

    await bot.set_my_commands(commands=group_commands, scope=BotCommandScopeAllGroupChats())

    personal_commands = [
        BotCommand(command="start", description="Познакомиться с работой бота 🎯"),
        BotCommand(command="help", description="Посмотреть инструкцию привязки чатов 🆘"),
        BotCommand(command="summ", description="Получить суммаризацию 🧠"),
    ]

    await bot.set_my_commands(commands=personal_commands, scope=BotCommandScopeAllPrivateChats())

async def main():
    await set_bot_commands(bot)
    print('-- Start polling --')

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())