import base64
from decimal import Decimal
from typing import Any, List, Callable, Union

import ujson
from aiogram import types

from core.pure import to_decimal
from handlers_bot.node import Node, RenderProps, is_cq
from i18n import _


class Confirm(Node):
    emoji = '✅'

    next: Node = None
    confirm_msg: Callable[[], str]
    custom_title: Callable[[], str]
    data: Any

    back_btn = True
    print_footer = False

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.children.append([self.next])

    @property
    def _full_title(self) -> str:
        return self.custom_title()

    @property
    def header(self) -> str:
        return '✅ ' + _('Confirmation')

    @property
    def message(self) -> str:
        return _('Are you sure you want to {msg}?').format(msg=self.confirm_msg())

    def buttons(self) -> List[List[types.InlineKeyboardButton]]:
        """
        Transform child nodes into buttons
        :return:
        """
        children = [[node.as_button(from_state=self.state, data={'d': self.data}) for node in group] for group in
                    self.children]
        children[0][0].text = '✅ ' + _('Confirm')
        return children

    def as_button(self, from_state, data: Union[dict, None] = None) -> types.InlineKeyboardButton:
        return super(Confirm, self).as_button(from_state, {'d': self.data})

    async def render(self, update: Union[types.CallbackQuery, types.Message]) -> RenderProps:
        if is_cq(update):
            data = ujson.loads(base64.b64decode(update.data))
            self.data = to_decimal(data['d'])
        return RenderProps()


def confirm_ton(amount: Decimal, next: Any, confirm_msg: Callable[[], str]) -> Confirm:
    return Confirm(data=amount,
                   confirm_msg=confirm_msg,
                   next=next(amount),
                   custom_title=lambda: f'{int(amount)} TON',
                   pass_data=amount)
