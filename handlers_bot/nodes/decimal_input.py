import decimal
from decimal import Decimal
from typing import Any, Union, Callable, List

from aiogram import types

from core.config_loader import config
from core.pure import to_decimal
from handlers_bot.node import Node, RenderProps, is_msg
from handlers_bot.nodes.confirm import confirm_ton
from i18n import _


class DecimalInput(Node):
    min: Decimal = to_decimal(1)
    max: Decimal = to_decimal(100)
    amounts = [[to_decimal(1), to_decimal(10)], [to_decimal(50), to_decimal(100)]]

    on_text = True
    back_btn = True

    error_msg = ''
    next_node: Callable[[Decimal], Node] = None  # Decimal -> Node
    confirm_text: Callable[[], str] = lambda: _('input {amount} TON')

    children = [
        []
    ]

    def __init__(self, **data: Any):
        super().__init__(**data)
        buttons = []
        for group in self.amounts:
            buttons.append([
                confirm_ton(x, self.next_node, lambda: self.confirm_text().format(amount=x)) for x in group
            ])
        self.children = buttons + self.children


    @property
    def footer(self) -> str:
        return _('Please enter or choose the amount')

    @property
    def custom_text(self) -> str:
        return ''

    @property
    def message(self) -> str:
        return _('{error}{text}'
                 'Limits:\n'
                 '• Minimum: {min}\n'
                 '• Maximum: {max}').format(
            text=self.custom_text + '\n\n' if self.custom_text else '',
            error='🚫 ' + f'*{self.error_msg}*' + '\n\n' if self.error_msg else '',
            min=self.min,
            max=self.max)

    async def pre_render(self):
        self.error_msg = ''

    async def render(self,
                     update: Union[types.CallbackQuery, types.Message]) -> RenderProps:
        props = RenderProps()
        if is_msg(update):
            await update.delete()
            self.logger.info('got new message')
            try:
                amount = to_decimal(update.text.replace(',', '.'))
            except decimal.InvalidOperation:
                self.error_msg = _('The entered value is not a number.')
                return props

            if amount < self.min:
                self.error_msg = _('The entered number is less than the minimum.')
            elif amount > self.max:
                self.error_msg = _('The entered number is greater than the maximum.')
            confirm = confirm_ton(amount, self.next_node, lambda: self.confirm_text().format(amount=amount))
            confirm.ancestor = self
            props.redirect_to = confirm
            return props
        return props

