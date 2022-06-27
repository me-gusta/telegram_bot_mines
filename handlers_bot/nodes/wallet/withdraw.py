from contextlib import suppress
from decimal import Decimal
from typing import Union, List

from aiogram import types
from aiogram.utils.exceptions import TelegramAPIError
from pydantic import BaseModel

from bot import bot
from core.config_loader import config
from core.pure import to_decimal
from core.aiogram_nodes.node import Node, TransitionButton, Button, ErrorNode
from core.aiogram_nodes.util import is_cq
from db.engine import session
from db.models import WithdrawRequest as WR
from handlers_bot.nodes.confirm import Confirm
from handlers_bot.nodes.decimal_input import DecimalInput
from core.aiogram_nodes.util import get_current_user
from i18n import _


class ConfirmWithdrawalAdmin(Node):
    emoji = Confirm.emoji
    only_admin = True

    class Props(BaseModel):
        request_id: int = 0
        msg: str = ''

    @property
    def title(self) -> str:
        return _('Confirm')

    @property
    def text(self) -> str:
        return self.props.msg

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if not is_cq(update):
            pass
        request: WR = session.query(WR).filter(WR.id == self.props.request_id).first()
        if not request:
            self._logger.error('cannot find request with id %s', self.props.request_id)
            return ErrorNode(msg='Cannot find request')
        if request.is_payed:
            self._logger.warn('request is paid %s', request)
            return ErrorNode(msg='request is paid')
        if request.user.balance < request.amount:
            self._logger.warn('request is paid %s', request)
            with suppress(TelegramAPIError):
                await bot.send_message(
                    chat_id=request.user.user_id,
                    text=_('❌ Your withdrawal request has been declined.\n'
                           'Reason: not enough funds in your wallet'),
                    reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                        TransitionButton(to_node='MainMenu', text='Main Menu').compile()
                    ]])
                )
            return ErrorNode(msg=f'user has not enough funds\n'
                                 f'balance: {request.user.balance}\n'
                                 f'amount: {request.amount}')

        return None


class WithdrawRules(Node):
    back_btn = True

    @property
    def title(self) -> str:
        return _('About withdrawals')

    @property
    def text(self) -> str:
        return _('⚠ Withdrawals can take up to 24h\n'
                 '⚠ Minimum amount: 0.5 💎\n'
                 '⚠ Maximum amount: 1000 💎\n '
                 '⚠ You can still use your assets while withdrawal request is pending\n')


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
        amount = to_decimal(self.props.data)
        if is_cq(update):
            self._logger.info('request withdraw: %s', amount)
        user = get_current_user()
        request = WR(user=user, amount=amount)
        session.add(request)
        session.commit()
        await bot.send_message(
            chat_id=config.operator_id,
            text=f'New withdrawal request\n'
                 f'User: {user}\n'
                 f'User balance: {user.balance}\n'
                 f'Amount:{request.amount}',
            reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                TransitionButton(to_node=ConfirmWithdrawalAdmin, props={'request_id': request.id}).compile()
            ]])
        )
        return None


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
