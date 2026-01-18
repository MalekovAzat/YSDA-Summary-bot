from datetime import datetime, timedelta
from src.command_dispatcher import dp
from aiogram.filters import Command
from aiogram import Bot, types, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

import re
from database.database import AsyncSessionLocal
from aiogram.types import InlineKeyboardButton

from src.user_service.user_service import UserService
from src.user_chat_service.user_chat_service import UserChatService

from src.tools import tools
from src.bot_utils import summarize_messages


@dp.message(Command(commands=['start']), F.chat.type == "private")
async def start_command_handler(message: types.Message):
    [telegram_chat_id, first_name, last_name, username, language_code ] = [message.chat.id, message.from_user.first_name, message.from_user.last_name, message.from_user.username, message.from_user.language_code]

    user_service = UserService()

    await user_service.get_or_create(telegram_chat_id, first_name, last_name, username, language_code)

    await message.answer('<b>Привет я бот который поможет тебе быть всегда в контексте и не терять важные апдейты!</b>\n\nПерешли мне сообщение из чата', parse_mode='HTML')

def is_group_forward_message(text: str):
    """
    Проверяет, что текст имеет формат chat_id:message_id:message_id для супергруппы.
    Возвращает True, если текст похож на идентификатор супергруппы с message_id.
    """
    return bool(re.match(r"^-100\d+:\d+:\d+$", text))

@dp.message(F.chat.type == "private", ~F.text.startswith("/"))
async def handle_message(message: types.Message, bot: Bot):
    text = message.text

    user_service = UserService()
    user = await user_service.get_by_telegram_id(telegram_id=message.from_user.id)

    if is_group_forward_message(text):
        [chat_id, tmp_message_id, second_tmp_message_id] = text.split(':')

        chat_id = int(chat_id)
        tmp_message_id = int(tmp_message_id)
        second_tmp_message_id = int(second_tmp_message_id)

        await bot.delete_message(chat_id=chat_id, message_id=tmp_message_id)
        await bot.delete_message(chat_id=chat_id, message_id=second_tmp_message_id)


        user_id = message.from_user.id
        result = await bot.get_chat_member(chat_id, user_id)

        if result.status not in ['member', 'administrator', 'creator']:
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
            text='Чат добавлен в список чатов, теперь по нему можем получать суммаризацию /summ'
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

    buttons: list[InlineKeyboardButton] = [
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

    buttons: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text= 'За последние 3 часа',
            callback_data=f'time:hours3;select_chat:${selected_chat_id}',
        ),
        InlineKeyboardButton(
            text= 'За день',
            callback_data=f'time:days1;select_chat:${selected_chat_id}',
        ),
        InlineKeyboardButton(
            text= 'За 3 дня',
            callback_data=f'time:days3;select_chat:${selected_chat_id}',
        ),
        InlineKeyboardButton(
            text= 'За неделю',
            callback_data=f'time:days7;select_chat:${selected_chat_id}',
        ),
        InlineKeyboardButton(
            text= 'Укажите свою начальную дату',
            callback_data=f'custom_time;select_chat:${selected_chat_id}',
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

def _get_time_delta(selected_time: str) -> timedelta:
    if selected_time.startswith("hours"):
        return timedelta(hours=int(selected_time.replace("hours", "")))
    elif selected_time.startswith("days"):
        return timedelta(days=int(selected_time.replace("days", "")))
    else:
        return timedelta()
    

@dp.callback_query(lambda c: c.data and c.data.startswith("time:"))
async def handle_time_selected(query: types.CallbackQuery, bot: Bot):
    time_info, chat_info = query.data.split(';')
    selected_time = time_info.replace('time:', '')
    curr_date = datetime.now()
    start_date = curr_date - _get_time_delta(selected_time)

    selected_chat_id = int(chat_info.replace('select_chat:$', ''))

    tmp_message = await bot.send_message(
        chat_id=query.message.chat.id,
        text='🫡Подготовливаю суммаризацию...'
    )

    await bot.send_chat_action(query.message.chat.id, 'typing')
    reply_text = await summarize_messages(selected_chat_id, bot.id, start_date, curr_date)

    await bot.edit_message_text(
        chat_id=query.message.chat.id,
        message_id=tmp_message.message_id,
        text=reply_text, parse_mode='MarkdownV2'
    )

class Form(StatesGroup):
    selected_chat_id = State()
    start_time = State()

@dp.callback_query(lambda c: c.data and c.data.startswith("custom_time"))
async def handle_time_selected(query: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.start_time)
    await query.message.answer("Введите свою начальную дату в формате ДД.ММ.ГГ:")
    query.message.delete()

    _, chat_info = query.data.split(';')

    selected_chat_id = int(chat_info.replace('select_chat:$', ''))
    await state.update_data(selected_chat_id=selected_chat_id)
    await state.set_state(Form.start_time)



@dp.message(Form.start_time)
async def handle_custom_time(message: types.Message, state: FSMContext):
    await message.reply("Обрабатываю...")
    date_str = message.text
    try:
        date = datetime.strptime(date_str, "%d.%m.%y")
    except:
        message.reply("Не смог прочитать дату, попробуйте ещё раз!")
        await state.clear()
        return
    
    curr_date = datetime.now()
    
    data = await state.get_data()
    selected_chat_id = int(data['selected_chat_id'])

    tmp_message = await message.answer(
        text='🫡Подготовливаю суммаризацию...'
    )

    await message.bot.send_chat_action(message.chat.id, 'typing')
    reply_text = await summarize_messages(selected_chat_id, message.bot.id, date, curr_date)

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=tmp_message.message_id,
        text=reply_text, parse_mode='MarkdownV2'
    )
    

