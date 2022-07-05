from typing import Union, List

from aiogram import types

from bot import bot
from core.config_loader import config
from core.constants import URL_NEWS, URL_SUPPORT
from db.engine import session
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
        user = get_current_user()
        msg = _('🖐 {welcome}, {name}!\n'
                '👛 Your balance: {balance} 💎').format(
            welcome=_('hello').capitalize(),
            name=user.first_name,
            balance=user.balance)

        if user.deposit_bonus:
            msg += '\n\n🎁 ' + _('*You have deposit bonus +{bonus}%*').format(bonus=user.deposit_bonus)
        return msg

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [TransitionButton(to_node=Games)],
            [TransitionButton(to_node=CryptoBotDI),
             TransitionButton(to_node=WithdrawDI)],
            [URLButton(url=URL_NEWS, text='📰 ' + _('News')), URLButton(url=URL_SUPPORT, text='🆘 ' + _('Support'))],
            [TransitionButton(to_node=Settings), TransitionButton(to_node=Referral)]
        ]

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        user = get_current_user()
        self._logger.info(user)
        self._logger.info(user.last_active, user.date_registered)
        if is_msg(update):
            if user.last_active == user.date_registered:
                referrer_id = User.ref_decode(update.get_args())
                self._logger.info('new user')
                referrer: User = session.query(User).filter(User.user_id == referrer_id).first()
                if referrer:
                    self._logger.info(f'referer: {referrer}')
                    user.deposit_bonus = config.referral_deposit_bonus
                    user.referrer_user_id = referrer.user_id
                await bot.send_message(chat_id=config.operator_id, text=f'New User\n'
                                                                        f'user: {user}\n'
                                                                        f'date: {user.date_registered}\n'
                                                                        f'referrer: {referrer}')
        return
