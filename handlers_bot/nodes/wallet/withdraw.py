from decimal import Decimal
from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from core.config_loader import config
from core.pure import to_decimal
from core.aiogram_nodes.node import Node, TransitionButton, Button
from core.aiogram_nodes.util import is_cq
from handlers_bot.nodes.decimal_input import DecimalInput
from core.aiogram_nodes.util import get_current_user
from i18n import _


class WithdrawRules(Node):
    back_btn = True

    @property
    def title(self) -> str:
        return _('About withdrawals')

    @property
    def text(self) -> str:
        return _('⚠ Withdrawals can take up to 24h\n'
                 '⚠ Minimum amount: 0.5 💎\n'
                 '⚠ Maximum amount: 1000 💎')


class WithdrawRequest(Node):
    emoji = '⌛'

    menu_btn = True

    class Props(BaseModel):
        data: Decimal = Decimal(0)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if isinstance(self.data, float):
                self.data = to_decimal(self.data)

    @property
    def title(self) -> str:
        return _('Withdrawal Request')

    @property
    def message(self) -> str:
        return _('⚠ Your withdrawal request is being processed\n'
                 '⚠ Withdrawals can take up to 24h\n'
                 '⚠ Conversion rate: 1 💎 = 1 TON')

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if is_cq(update):
            self._logger.info('request withdraw: %s', self.props.data)
        return


class WithdrawDI(DecimalInput):
    emoji = '💳'
    min = config.wallet.min_withdraw
    max = config.wallet.max_withdraw

    next_state = WithdrawRequest.state()
    back_to = 'MainMenu'

    @property
    def title(self) -> str:
        return _('Withdraw')

    @property
    def footer(self) -> str:
        return _('Please enter or choose the amount for withdrawal.')

    @property
    def confirm_msg(self) -> str:
        return _('withdraw {amount} TON')

    @property
    def custom_text(self) -> str:
        return _('👛 Your Balance: {balance} 💎').format(balance=get_current_user().balance)

    @property
    def buttons(self) -> List[List[Button]]:
        buttons = super(WithdrawDI, self).buttons

        buttons += [
            [TransitionButton(to_node=WithdrawRules)]
        ]
        return buttons

    def __init__(self, **data):
        super(WithdrawDI, self).__init__(**data)

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        out = await super(WithdrawDI, self).process(update)
        user = get_current_user()
        if user.balance < config.wallet.min_withdraw:
            self.props.error_msg = _('Sorry, your balance is less than the required minimum for withdrawal.')
            return

        if user.balance < self.props.amount:
            self.props.error_msg = _('Your balance is less than the entered amount')
            return
        return out
