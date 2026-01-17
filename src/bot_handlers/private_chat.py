from src.command_dispatcher import dp
from aiogram.filters import Command
from aiogram import Bot, types, F
import re
from database.database import AsyncSessionLocal
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.user_service.user_service import UserService
from src.user_chat_service.user_chat_service import UserChatService

from src.tools import tools


@dp.message(Command(commands=['start']), F.chat.type == "private")
async def start_command_handler(message: types.Message):
    [telegram_chat_id, first_name, last_name, username, language_code ] = [message.chat.id, message.from_user.first_name, message.from_user.last_name, message.from_user.username, message.from_user.language_code]

    user_service = UserService()

    await user_service.get_or_create(telegram_chat_id, first_name, last_name, username, language_code)

    await message.answer('<B>Привет я бот который поможет тебе быть всегда в контексте и не терять важные апдейты!</b>\n\nПерешли мне сообщение из чата', parse_mode='HTML')

def is_supergroup_id(chat_id: str):
    return bool(re.match(r"^-100\d{9,}$", chat_id))

@dp.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_message(message: types.Message, bot: Bot):
    text = message.text

    user_service = UserService()
    user = await user_service.get_by_telegram_id(telegram_id=message.from_user.id)

    if is_supergroup_id(text):
        chat_id = int(text)
        user_id = message.from_user.id
        result = await bot.get_chat_member(chat_id, user_id)

        if result.status not in ['member', 'administrator']:
            await bot.send_message(user_id, "Вы не являетесь членом этого чата, суммаризация недоступна")
            return

        chat_info = await bot.get_chat(chat_id)

        async with AsyncSessionLocal() as db:
            from src.database.models.user_chats import UserChats
            user_chats_obj = UserChats(
                user_id=user.id,
                chat_id=chat_id,
                role=result.status,
                title=chat_info.title
            )

            db.add(user_chats_obj)
            await db.commit()

        # в личных сообщениях идентификатор чата и пользователя совпадают
        await bot.send_message(
            chat_id=user_id,
            text='Чат добавлен в список чатов, теперь можем получать суммаризацию /summ'
        )

@dp.message(Command(commands=['summ']), F.chat.type == 'private')
async def handle_summ_command(message: types.Message, bot: Bot):
    user_service = UserService()
    chat_service = UserChatService()

    user = await user_service.get_by_telegram_id(
        telegram_id=message.from_user.id
    )

    chats = await chat_service.get_by_user_id(user.id)

    if len(chats) == 0:
        await message.reply('У вас нет чатов по которым можно провести summary')
        return

    buttons = [InlineKeyboardButton(text=f'{chat_record.title}',callback_data=f'select_chat:${chat_record.chat_id}') for chat_record in chats]

    kb = tools.build_inline_keyboard(buttons, 2)

    await bot.send_message(
        chat_id= user.telegram_id,
        text='Выберите чат по которому вы хотите получить суммаризацию:',
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data and c.data == 'chat_list')
async def show_chat_list(query: types.CallbackQuery, bot: Bot):
    user_service = UserService()
    chat_service = UserChatService()

    user = await user_service.get_by_telegram_id(query.from_user.id)
    chats = await chat_service.get_by_user_id(user.id)

    if not chats:
        await bot.edit_message_text(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            text="У вас нет чатов по которым можно провести summary"
        )
        await query.answer()
        return

    buttons: List[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text=f'{chat_record.title}',
            callback_data=f'select_chat:${chat_record.chat_id}'
        )
        for chat_record in chats
    ]

    kb = tools.build_inline_keyboard(buttons, 2)

    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        text="Выберите чат по которому вы хотите получить суммаризацию:",
        reply_markup=kb
    )

    await query.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("select_chat:$"))
async def handle_chat_selected(query: types.CallbackQuery, bot: Bot):
    user_service = UserService()
    chat_service = UserChatService()

    selected_chat_id = int(query.data.replace('select_chat:$', ''))

    user = await user_service.get_by_telegram_id(query.from_user.id)

    chat = await chat_service.get_one(selected_chat_id, user.id)

    buttons: List[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text= 'За последний час',
            callback_data='chat_list',
        ),
        InlineKeyboardButton(
            text= 'За день',
            callback_data='chat_list',
        ),
        InlineKeyboardButton(
            text= 'За 3 дня',
            callback_data='chat_list',
        ),
        InlineKeyboardButton(
            text= 'За неделю',
            callback_data='chat_list',
        ),
        InlineKeyboardButton(
            text= '⬅️ Назад',
            callback_data='chat_list',
        )
    ]

    kb = tools.build_inline_keyboard(buttons, 2)

    await bot.edit_message_text(
        text=f"Выбран чат <b>{chat.title}</b>\n\n Выберите доступные опции:", 
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=kb,
        parse_mode='HTML'
    )

    await query.answer()

