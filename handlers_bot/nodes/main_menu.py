from typing import Union

from aiogram import types

from db.models import User
from handlers_bot.node import Node, is_msg, RenderProps, is_cq
from handlers_bot.nodes.games import Games
from handlers_bot.nodes.wallet.deposit import Deposit
from i18n import _


class MainMenu(Node):
    print_header = False
    commands = ['start', 'help']

    children = [
        [Games()],
        [Deposit()]
    ]

    @property
    def message(self) -> str:
        return _('{welcome}, {name}!\n'
                 '_Your balance_: {balance} 💎').format(
            welcome=_('hello'),
            name=self.user.first_name,
            balance=self.user.balance)

    async def render(self,
                     update: Union[types.CallbackQuery, types.Message]) -> RenderProps:
        props = RenderProps()
        if is_msg(update):
            referrer_id = User.ref_decode(update.get_args())
            self.logger.info(f'Referer: {referrer_id}')
            props.new_message = True
        return props
