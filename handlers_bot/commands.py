from aiogram import types
from aiogram.utils.deep_linking import decode_payload

from bot import bot
from core.config_loader import config
from core.logging_config import root_logger
from db.helpers import get_or_create_user
from db.models import User
from handlers_bot.common import generate_main_menu

from i18n import _


async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    referrer_id = User.ref_decode(message.get_args())
    user = await get_or_create_user(message.from_user, referrer_user_id=referrer_id)
    root_logger.info(f'START command. {user}, referrer = {referrer_id}')

    text, buttons = generate_main_menu(user)

    keyboard_markup = types.InlineKeyboardMarkup(1, inline_keyboard=buttons)
    await bot.send_message(message.chat.id, text, reply_markup=keyboard_markup, parse_mode='markdown')
