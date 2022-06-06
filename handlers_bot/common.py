import random
from contextlib import suppress
from decimal import Decimal
from typing import List, Union

from aiogram import types
from aiogram.utils.exceptions import MessageNotModified

from core.constants import SUPPORT_USERNAME
from core.pure import to_decimal
from db.engine import session
from db.models import User, UserState
from i18n import _


def get_flag(language_code: str):
    if language_code == 'ru':
        return '🇷🇺'
    else:
        return '🇬🇧'


def random_welcome():
    phrases = [
        _('hello'), _('hello'), _('hello'),
        _('you look great today'), _('nice to see you again'),
        _('hello'), _('you look great today'), _('nice to see you again'), _('have a nice day'),
        _('good luck')
    ]
    return random.choice(phrases).capitalize()


async def answer_query(query: types.CallbackQuery, text: str,
                       buttons: List[List[types.InlineKeyboardButton]]):
    with suppress(MessageNotModified):
        await query.message.edit_text(text,
                                      reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=buttons),
                                      parse_mode='markdown')
    await query.answer()


def generate_main_menu(user: User) -> (str, List[List[types.InlineKeyboardButton]]):
    if user.state != UserState.NONE:
        user.state = UserState.NONE
        session.commit()
    text = _('{welcome}, {name}!\n'
             '_Your balance_: {balance} 💎\n\n'
             '*Choose an option*').format(
        welcome=random_welcome(),
        name=user.first_name,
        balance=user.balance,
    )
    buttons = [
        # [types.InlineKeyboardButton('Start Game', web_app=types.WebAppInfo(url=config.webapp_url))],
        [types.InlineKeyboardButton('🕹️ ' + _('Games'), callback_data=GamesCQ.GAMES)],
        [types.InlineKeyboardButton('👛 ' + _('Wallet'), callback_data=WalletCQ.WALLET)],
        [types.InlineKeyboardButton('📰 ' + _('News'), url='https://t.me/SupaMegaHelp')],
        [types.InlineKeyboardButton(get_flag(user.language_code) + ' ' + _('Language'),
                                    callback_data=LanguageCQ.CHOICE),
         types.InlineKeyboardButton('🆘 ' + _('Support'), url='https://t.me/' + SUPPORT_USERNAME)]
    ]
    return text, buttons


class MenuCQ:
    MENU = 'menu'
    WALLET = 'menu-wallet'
    BACK = 'menu-back'


class GamesCQ:
    GAMES = 'games'
    PLACEHOLDER = 'games-placeholder'


class WalletCQ:
    WALLET = 'wallet'
    DEPOSIT = 'wallet-deposit'
    WITHDRAW = 'wallet-withdraw'
    WITHDRAW_INFO = 'wallet-info'
    HELP = 'wallet-help'

    WITHDRAW_REQUEST = 'withdraw-request-'

    @staticmethod
    def withdraw_request(n: Union[int, float, Decimal]) -> str:
        if isinstance(n, Decimal):
            return WalletCQ.WITHDRAW_REQUEST + str(n)
        else:
            return WalletCQ.WITHDRAW_REQUEST + str(to_decimal(n))

    @staticmethod
    def withdraw_request_get(query: types.CallbackQuery) -> Decimal:
        return to_decimal(query.data.removeprefix(WalletCQ.WITHDRAW_REQUEST))


class CryptoBotCQ:
    PAYMENT_OPTION = 'cryptobot-payment'
    CUSTOM_AMOUNT = 'cryptobot-custom'

    CONFIRM = 'cryptobot-confirm-'

    @staticmethod
    def confirm(n: Union[int, float]) -> str:
        return 'cryptobot-confirm-' + str(to_decimal(n))

    @staticmethod
    def confirm_get(query: types.CallbackQuery) -> float:
        return float(query.data.removeprefix(CryptoBotCQ.CONFIRM))

    DEPOSIT = 'cryptobot-deposit-'

    @staticmethod
    def deposit(n: Union[int, float, Decimal]) -> str:
        if isinstance(n, Decimal):
            return CryptoBotCQ.DEPOSIT + str(n)
        else:
            return CryptoBotCQ.DEPOSIT + str(to_decimal(n))

    @staticmethod
    def deposit_get(query: types.CallbackQuery) -> Decimal:
        return to_decimal(query.data.removeprefix(CryptoBotCQ.DEPOSIT))


class LanguageCQ:
    CHOICE = 'language'
    SET = 'language-set-'

    @staticmethod
    def set(language_code) -> str:
        return LanguageCQ.SET + language_code

    @staticmethod
    def set_get(query) -> str:
        return query.data.removeprefix(LanguageCQ.SET)


class WithdrawRequestAcceptCQ:
    ACCEPT = 'withdraw_request_accept-'

    @staticmethod
    def accept(request_id: int):
        return WithdrawRequestAcceptCQ.ACCEPT + str(request_id)
    @staticmethod
    def accept_get(query) -> Decimal:
        return to_decimal(query.data.removeprefix(WithdrawRequestAcceptCQ.ACCEPT))

