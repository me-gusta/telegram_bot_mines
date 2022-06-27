from contextlib import suppress

from aiogram import types
from aiogram.utils.exceptions import MessageNotModified

from core.aiogram_nodes.node import Shortcuts
from core.aiogram_nodes.state_management import StateManager
from core.aiogram_nodes.telegram_dispatcher import TelegramDispatcher
from core.aiogram_nodes.util import decode_callback_data, encode_callback_data
from handlers_bot.nodes.main_menu import MainMenu
from i18n import _


async def callback_query_fallback(query: types.CallbackQuery):
    text = _('😐 *Oops....*\n'
             'Something unexpected happened.')
    buttons = [
        [types.InlineKeyboardButton(MainMenu().title, callback_data=encode_callback_data({Shortcuts.TRANSITION_TO_NODE: MainMenu.state()}))]
    ]
    with suppress(MessageNotModified):
        await query.message.edit_text(text,
                                      reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=buttons),
                                      parse_mode='markdown')
    await query.answer()


def setup(dp: TelegramDispatcher):

    dp.register_callback_query_handler(callback_query_fallback)