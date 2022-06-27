from typing import Union, List

from aiogram import types

from core.constants import URL_NEWS, URL_SUPPORT
from db.models import User
from core.aiogram_nodes.node import Node, Button, TransitionButton, URLButton
from core.aiogram_nodes.util import is_msg
from handlers_bot.nodes.games import Games
from handlers_bot.nodes.referral import Referral
from handlers_bot.nodes.settings import Settings
from handlers_bot.nodes.wallet.deposit import CryptoBotDI
from handlers_bot.nodes.wallet.withdraw import WithdrawDI
from core.aiogram_nodes.util import get_current_user
from i18n import _

def random_welcome():
    phrases = [
        _('hello'), _('hello'), _('hello'),
        _('you look great today'), _('nice to see you again'),
        _('hello'), _('you look great today'), _('nice to see you again'), _('have a nice day'),
        _('good luck')
    ]
    return _('hello')

class MainMenu(Node):
    emoji = '🏠'
    commands = ['start', 'help', 'menu']

    @property
    def title(self) -> str:
        return _('Main Menu')

    @property
    def text(self) -> str:
        return _('🖐 {welcome}, {name}!\n'
                 '👛 Your balance: {balance} 💎').format(
            welcome=_('hello').capitalize(),
            name=get_current_user().first_name,
            balance=get_current_user().balance)

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [TransitionButton(to_node=Games)],
            [TransitionButton(to_node=CryptoBotDI),
             TransitionButton(to_node=WithdrawDI)],
            [URLButton(url=URL_NEWS, text='📰 ' + _('News')), URLButton(url=URL_SUPPORT, text='🆘 ' + _('Support'))],
            [TransitionButton(to_node=Settings), TransitionButton(to_node=Referral)]
        ]

    def _compile_markup(self) -> types.InlineKeyboardMarkup:
        keyboard = super(MainMenu, self)._compile_markup()
        keyboard.add(types.InlineKeyboardButton(text='lol', callback_data='shma'))
        return keyboard

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if is_msg(update):
            referrer_id = User.ref_decode(update.get_args())
            self._logger.info(f'Referer: {referrer_id}')
        return
