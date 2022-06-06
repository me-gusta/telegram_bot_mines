from aiogram import types, Dispatcher

from core.config_loader import config
from core.constants import AVAILABLE_TRANSLATIONS
from db.engine import session
from db.helpers import get_or_create_user
from handlers_bot.callbacks.wallet import setup as setup_wallet
from handlers_bot.common import answer_query, MenuCQ, generate_main_menu, GamesCQ, get_flag, LanguageCQ
from i18n import _


async def games(query: types.CallbackQuery):
    """ Show available games """
    text = _('🕹️ Games\n'
             '💣 *Mines*: Uncover all diamonds to maximize your profit!\n'
             '💸 *Coinflip*: _[soon]_ Simple 50-50 game of chance.\n'
             '🚀 *Rocket Launch*: _[soon]_ Hop on a starship and earn up to x10000!\n\n'
             '_You can play every game for free if you set your bet to 0_\n\n'
             '*Choose a game*')

    buttons = [
        [types.InlineKeyboardButton('💣 ' + _('Mines'), web_app=types.WebAppInfo(url=config.webapp_url))],
        [types.InlineKeyboardButton('💸 ' + _('Coinflip'), callback_data=GamesCQ.PLACEHOLDER)],
        [types.InlineKeyboardButton('🚀 ' + _('Rocket Launch'), callback_data=GamesCQ.PLACEHOLDER)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=MenuCQ.MENU)]
    ]

    await answer_query(query, text, buttons)


async def game_placeholder(query: types.CallbackQuery):
    await query.answer(
        text=_('This game is still in development. Subscribe to our 📰 News to get notified!'), show_alert=True)


async def menu(query: types.CallbackQuery):
    user = get_or_create_user(query.from_user)
    text, buttons = generate_main_menu(user)

    await answer_query(query, text, buttons)


async def language_choice(query: types.CallbackQuery):
    user = get_or_create_user(query.from_user)
    text = _('Your current language: {language}\n\n'
             '*Choose a language*').format(
        language=get_flag(user.language_code) + ' ' + user.language_code
    )

    buttons = [
        [types.InlineKeyboardButton(
            text=get_flag(code) + ' ' + code,
            callback_data=LanguageCQ.set(code)
        )] for code in AVAILABLE_TRANSLATIONS
    ]

    await answer_query(query, text, buttons)


async def language_set(query: types.CallbackQuery):
    user = get_or_create_user(query.from_user, do_commit=False)
    code = LanguageCQ.set_get(query)
    if code not in AVAILABLE_TRANSLATIONS:
        code = 'en'
    user.language_code = code
    session.commit()
    await menu(query)


async def close(query: types.CallbackQuery):
    await query.message.delete()

def setup(dp: Dispatcher):
    dp.register_callback_query_handler(menu,
                                       lambda call: call.data == MenuCQ.MENU)

    dp.register_callback_query_handler(games,
                                       lambda call: call.data == GamesCQ.GAMES)
    dp.register_callback_query_handler(game_placeholder,
                                       lambda call: call.data == GamesCQ.PLACEHOLDER)
    dp.register_callback_query_handler(language_choice,
                                       lambda call: call.data == LanguageCQ.CHOICE)
    dp.register_callback_query_handler(language_set,
                                       lambda call: call.data.startswith(LanguageCQ.SET))

    dp.register_callback_query_handler(close, lambda call: call.data == 'close')

    setup_wallet(dp)
