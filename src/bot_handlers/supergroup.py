
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

<b>Я могу помочь:</b>
- 📌 Выделить главные темы из переписки.
- 📝 Соберу обсуждения в темы и итоги.
- ⚡ Соберу краткое резюме за выбранный период.

<b>Команды для суммаризации:</b>
- 📅 /summ YY-MM-DD — суммаризация за конкретный день
- ⏱ /summ_1h — суммаризация за последний час
- 🕒 /summ_3h — суммаризация за последние 3 часа
- 🌞 /summ_today — суммаризация за сегодня
- 🌙 /summ_yesterday — суммаризация за вчера
- 📊 /summ_week — суммаризация за неделю

<b>Другие команды:</b>
- 🚀 /start — получить список команд
- 📥 /import — импортировать сообщения чата (только для админа)
- 🆔 /chat_id — получить идентификатор чата

<b>Как пользоваться:</b>
1. Добавьте меня в чат и дайте права администратора (для чтения сообщений и суммаризации).
2. Выбирайте нужную команду из списка выше.
3. Сводка строится по сообщениям, которые я видел после добавления в чат.

<b>Так же ты можешь привязать чат в личке с ботом и запрашивать сводки от туда💋</b>
"""

    await bot.send_message(chat_id=message.chat.id, text=about, parse_mode='HTML')

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

    reply = await summarize_messages(message.chat.id, bot.id, date_from=date_obj, date_to=next_day)

    await bot.send_message(chat_id=message.chat.id, text=reply, parse_mode='MarkdownV2')


@dp.message(Command(commands=['chat_id']), F.chat.type == "supergroup")
async def handle_chat_id_command(message: types.Message, bot: Bot):
    tmp_message = await bot.send_message(\
        chat_id=message.chat.id, 
        text=f'{message.chat.id}:{message.message_id}'
    )

    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=tmp_message.message_id,
        text=f'{message.chat.id}:{message.message_id}:{tmp_message.message_id}'
    )


@dp.message(Command(commands=['import']), F.chat.type == "supergroup")
async def handle_save_history(message: types.Message, bot: Bot):
    bot_name = await bot.get_my_name()
    if not check_if_tagged(message, bot_name.name): # Ignore, if not mentioned
        pass
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_admin(bot, chat_id, user_id):
        await message.reply("Вы не обладаете правами администратора!")
        return

    document = message.document
    if not document:
        await message.reply('Для импорта необходимо прикрепить json файл с историей данного диалога')
        return

    tmp_message = await bot.send_message(
        message.chat.id,
        text='Начинаю импорт диалога...'
    )

    try:
        file_io = io.BytesIO()
        await message.bot.download(file=document.file_id, destination=file_io)
        file_io.seek(0)
        byte_data = file_io.read()
        json_data = json.loads(byte_data.decode("utf-8"))

        messages = convert_messages(json_data)

        await tmp_message.edit_text(f"Нашёл {len(messages)} сообщений. Запоминаю...")

        async with AsyncSessionLocal() as db:
            chat_service = ChatService(db)
            await chat_service.save_history(messages)

        await tmp_message.edit_text("Импорт завершен, теперь я знаю историю диалога и помогу разобраться в деталях!")
    except Exception as e:
        print(e)
        await tmp_message.edit_text("К сожалению import завершился с ошибкой")

@dp.message(
    Command(commands=['summ_1h', 'summ_3h', 'summ_today', 'summ_yesterday', 'summ_week']),
    F.chat.type == 'supergroup'
)
async def handle_summ_commands(message: types.Message, bot: Bot):
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    command = message.text.split('@')[0]

    # Определяем период
    if command == '/summ_1h':
        date_from = now - timedelta(hours=1)
        date_to = now
    elif command == '/summ_3h':
        date_from = now - timedelta(hours=3)
        date_to = now
    elif command == '/summ_today':
        date_from = datetime(now.year, now.month, now.day)
        date_to = date_from + timedelta(days=1)
    elif command == '/summ_yesterday':
        date_from = datetime(now.year, now.month, now.day) - timedelta(days=1)
        date_to = date_from + timedelta(days=1)
    elif command == '/summ_week':
        start_of_week = now - timedelta(days=now.weekday())  # Пн этого месяца
        date_from = datetime(start_of_week.year, start_of_week.month, start_of_week.day)
        date_to = date_from + timedelta(days=7)
    else:
        await message.reply("Неизвестная команда")
        return

    tmp_message = await bot.send_message(
        chat_id=message.chat.id,
        text='🫡Подготовливаю суммаризацию...'
    )

    await bot.send_chat_action(message.chat.id, 'typing')

    reply_text = await summarize_messages(chat_id=message.chat.id, bot_id=bot.id, date_from=date_from, date_to=date_to)
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=tmp_message.message_id,
        text=reply_text, parse_mode='MarkdownV2'
    )


# After all handlers because it should be the lowest priority handler
@dp.message(F.chat.type == "supergroup", ~F.text.startswith("/"), F.content_type != ContentType.DOCUMENT)
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