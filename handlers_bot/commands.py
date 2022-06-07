from aiogram import types

from bot import bot
from core.config_loader import config
from db.helpers import get_or_create_user
from handlers_bot.common import generate_main_menu

from i18n import _


async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    # user = message.from_user.to_python()
    # print(user)
    user = await get_or_create_user(message.from_user)

    text, buttons = generate_main_menu(user)

    keyboard_markup = types.InlineKeyboardMarkup(1, inline_keyboard=buttons)
    await bot.send_message(message.chat.id, text, reply_markup=keyboard_markup, parse_mode='markdown')
