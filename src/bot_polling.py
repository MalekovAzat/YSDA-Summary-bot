import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated
from dotenv import load_dotenv
from database.database import AsyncSessionLocal
from sqlalchemy.future import select
from aiogram.types import BotCommand
from src.command_dispatcher import dp
import bot_handlers.private_chat
import bot_handlers.supergroup
from md2tgmd import escape

load_dotenv()


BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("DATABASE_URL is not set in environment variables")

bot = Bot(token=BOT_TOKEN)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Получить список команд"),
        BotCommand(command="chat_id", description="Получить идентификатор чата"),
        BotCommand(command="summ", description="За день /summ 25-15-10"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await set_bot_commands(bot)
    print('-- Start polling --')

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())