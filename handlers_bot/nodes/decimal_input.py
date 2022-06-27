import decimal
from decimal import Decimal
from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from core.pure import to_decimal
from core.aiogram_nodes.node import Node, TransitionButton, Button
from core.aiogram_nodes.util import is_msg
from handlers_bot.nodes.confirm import Confirm
from i18n import _


class DecimalInput(Node):
    next_state: str = '1'
    min: Decimal = to_decimal(1)
    max: Decimal = to_decimal(100)

    on_text = True

    class Props(BaseModel):
        amounts: List[List[Decimal]] = [[to_decimal(1), to_decimal(10)], [to_decimal(50), to_decimal(100)]]
        amount: Decimal = 0
        error_msg: str = ''

    @property
    def confirm_msg(self) -> str:
        return _('input {amount} TON')

    @property
    def custom_text(self) -> str:
        return _('----')

    @property
    def text(self) -> str:
        return _('{error}{text}'
                 'Limits:\n'
                 '• Minimum: {min}\n'
                 '• Maximum: {max}').format(
            text=self.custom_text + '\n\n' if self.custom_text else '',
            error='🚫 ' + f'*{self.props.error_msg}*' + '\n\n' if self.props.error_msg else '',
            min=self.min,
            max=self.max)

    @property
    def buttons(self) -> List[List[Button]]:
        def btn_text(x: Decimal):
            string = str(x).split('.')[0]
            return f'{string} TON'

        return [
            [TransitionButton(text=btn_text(x),
                              props={'amount': x, 'next_state': self.next_state},
                              to_node=self.state()) for x in group] for group in self.props.amounts
        ]

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if is_msg(update):
            await update.delete()
            self._logger.info('got new input. text = %s', update.text)
            try:
                amount = to_decimal(update.text.replace(',', '.'))
            except decimal.InvalidOperation:
                self.props.error_msg = _('The entered value is not a number.')
                return

            if amount < self.min:
                self.props.error_msg = _('The entered number is less than the minimum.')
                return
            elif amount > self.max:
                self.props.error_msg = _('The entered number is greater than the maximum.')
                return
            self.props.amount = amount

        if self.props.amount > 0:
            msg = self.confirm_msg.format(amount=self.props.amount)
            confirm = Confirm(back_to=self.state(),
                              msg=msg,
                              data=self.props.amount,
                              next_state=self.next_state)
            return confirm
