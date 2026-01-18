
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, types, F
from src.command_dispatcher import dp
from aiogram.types import ChatMemberUpdated
from sqlalchemy.future import select
from database.database import AsyncSessionLocal
from aiogram.types import InlineKeyboardButton
import re

from src.tools import tools
from src.chat_service.chat_service import ChatService
from src.summarizator_service.summarizator_service import SummarizationService
from md2tgmd import escape


@dp.message(Command(commands=['start', 'help']), F.chat.type == "supergroup")
async def start_command_handler(message: types.Message, bot: Bot):
    about = """
Привет! 👋 Я делаю краткие сводки по этому чату.

Я могу помочь:
- 📌 Выделить главные темы из переписки.
- 📝 Соберу обсуждения в темы и итоги.
- ⚡ Соберу в краткое резюме за выбранный период.

Как пользоваться:

1. Дай мне права администратора.
2. Запроси суммаризацию командой за конкретный день /summ YY-MM-DD.
3. Запроси суммаризацию за выбранный период: /summ YY-MM-DD YY-MM-DD.

Важно: сводка строится по сообщениям, которые я видел после добавления в чат.
"""

    await bot.send_message(chat_id=message.chat.id, text=about)

@dp.my_chat_member()
async def on_bot_added_to_chat(update: ChatMemberUpdated, bot: Bot):
    
    chat_id = update.chat.id
    chat = update.chat
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db)

        await chat_service.get_or_create_chat(chat.id, chat.title, chat.type)
        await chat_service.set_admin_status(chat.id, new_status == "administrator")

    if new_status in ["member", "administrator"] and old_status not in ["member", "administrator"]:
        await bot.send_message(
            chat_id,
            "Спасибо за добавление! 😊 Пожалуйста, выдайте мне права администратора — это нужно, чтобы я мог читать историю сообщений и делать корректные суммаризации чата."
        )

    elif old_status == "member" and new_status == "administrator":
        await bot.send_message(
            chat_id,
            "Теперь я администратор — готов работать с сообщениями ✅!"
        )

    elif old_status == "administrator" and new_status in ["member", "kicked"]:
        await bot.send_message(
            chat_id,
            "Я больше не администратор — часть функций может не работать ⚠️"
        )

@dp.message(F.chat.type == "supergroup", ~F.text.startswith("/"))
async def handle_any_message(message: types.Message):
    if message.new_chat_members or message.left_chat_member:
        return

    message_text = message.text or message.caption or ""
    if not message_text.strip():
        return

    message_text = message.text or message.caption or ""
    chat_id = message.chat.id
    message_id = message.message_id
    from_id = message.from_user.id

    internal_id = str(chat_id)[4:]
    message_link = f'https://t.me/c/{internal_id}/{message_id}'

    from_name = f'{message.from_user.first_name} {message.from_user.last_name}'

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db)
        await chat_service.save_message(
            message_id=message_id,
            chat_id=chat_id,
            from_id=from_id,
            text=message_text,
            link_in_chat=message_link,
            from_name=from_name
        )

        await db.commit()

@dp.message(Command(commands=["summary"]), F.chat.type == "supergroup")
async def handle_summ_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    buttons = [InlineKeyboardButton(text=f'{123}',callback_data=f'sc:u:{user_id}')]

    kb = tools.build_inline_keyboard(buttons=buttons, row_width=1)

    await bot.send_message(
        chat_id=chat_id,
        text='Давай подготовим для тебя новое summary по этому чату!\n\n',
        reply_markup = kb
    )

@dp.message(Command(commands=["summ"]), F.chat.type == "supergroup")
async def handle_summ_command(message: types.Message, bot: Bot):
    chat_id = message.chat.id

    date_str = message.text.split(' ')[-1]
    date_regex = r"\b\d{2}-\d{2}-\d{2}\b"
    if not re.fullmatch(date_regex, date_str):
        await message.reply(f'Формат даты должен быть YY-MM-DD')
        return

    from datetime import datetime, timedelta
    date_obj = datetime.strptime(date_str, "%y-%m-%d")
    next_day = date_obj + timedelta(days=1)

    reply: str = None

    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db)

        messages = await chat_service.get_messages_for_day(chat_id=chat_id, bot_id=bot.id, date_from=date_obj, date_to=next_day)

        if len(messages) == 0:
            await message.reply(f"Сообщений за эту дату нет., {date_obj, next_day}")
            return
        messages = [f"{msg.created_at.strftime('%d.%m.%Y %H:%M')} {msg.from_name} {msg.link_in_chat}: {msg.text}" for msg in messages]

    summarizator = SummarizationService()
    
    try:
        result = await summarizator.summarize_v2(messages)
        reply = escape(result)
    except Exception as e:
        result = 'Пу пу пуу...\n\nК сожалению суммаризация завершилась с ошибкой, нам очень жаль мы старались 😕'

    await bot.send_message(chat_id=message.chat.id, text=reply, parse_mode='MarkdownV2')


@dp.message(Command(commands=['chat_id']), F.chat.type == "supergroup")
async def handle_chat_id_command(message: types.Message):
    await message.reply(str(message.chat.id))