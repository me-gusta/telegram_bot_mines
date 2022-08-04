from contextlib import suppress
from decimal import Decimal
from typing import Union, List

import aiohttp
import ujson
from aiogram import types
from aiogram.utils.exceptions import TelegramAPIError
from pydantic import BaseModel
from ujson import JSONDecodeError

from bot import bot
from core.aiogram_nodes.node import Node, TransitionButton, Button, ErrorNode
from core.aiogram_nodes.util import get_current_user
from core.aiogram_nodes.util import is_cq
from core.config_loader import config
from core.constants import CRYPTO_PAY_URL
from core.pure import to_decimal
from db.engine import dbs
from db.helpers import get_user_by_user_id
from db.models import WithdrawRequest as WR, PyObjectId
from handlers_bot.nodes.confirm import Confirm
from handlers_bot.nodes.decimal_input import DecimalInput
from i18n import _


class ConfirmWithdrawalAdmin(Node):
    emoji = Confirm.emoji
    only_admin = True

    class Props(BaseModel):
        r: str = ''
        msg: str = ''

    @property
    def title(self) -> str:
        return _('Confirm')

    async def text(self) -> str:
        return self.props.msg

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if not is_cq(update):
            pass
        request_id = PyObjectId(self.props.r)
        request_query = await dbs.withdraw_requests.find_one({'_id': request_id})
        if not request_query:
            self._logger.error('cannot find request with id %s', request_id)
            return ErrorNode(msg='Cannot find request')
        request = WR(**request_query)
        request_user = await get_user_by_user_id(request.user_id)

        if request.is_payed:
            self._logger.warn('request is paid %s', request)
            return ErrorNode(msg='request is paid')
        if request_user.balance < request.amount:
            self._logger.warn('request is canceled. not enough funds %s', request)
            with suppress(TelegramAPIError):
                await bot.send_message(
                    chat_id=request_user.user_id,
                    text=_('❌ Your withdrawal request has been declined.\n'
                           'Reason: not enough funds in your wallet'),
                    reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                        TransitionButton(to_node='MainMenu', text='Main Menu').compile()
                    ]])
                )
            return ErrorNode(msg=f'user has not enough funds\n'
                                 f'balance: {request_user.balance}\n'
                                 f'amount: {request.amount}')
        if request_user.payed_games_played < 5:
            self._logger.warn('request is canceled. not enough payed_games_played %s', request)
            with suppress(TelegramAPIError):
                await bot.send_message(
                    chat_id=request_user.user_id,
                    text=_('❌ Your withdrawal request has been declined.\n'
                           'Reason: you need to play at least 5 payed games to unlock withdrawals\n'
                           'You played: {amount} games out of 5').format(amount=request_user.payed_games_played),
                    reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                        TransitionButton(to_node='MainMenu', text='Main Menu').compile()
                    ]])
                )
            return ErrorNode(msg=f'user has not enough payed games\n'
                                 f'{request_user.payed_games_played}/5')
        headers = {
            'Crypto-Pay-API-Token': config.crypto_pay_token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'asset': 'TON',
                'amount': request.amount,
                'user_id': request_user.user_id,
                'spend_id': str(hash(str(request.spend_id) + '.Iasgfuih'))}
        async with aiohttp.ClientSession(headers=headers) as client_session:
            resp = await client_session.post(CRYPTO_PAY_URL + 'transfer', data=data)
            text = await resp.text()
            if resp.status != 200:
                self._logger.error('response status %s. %s', resp.status, text)
                return ErrorNode(msg=f'Unable to transfer. response status: {resp.status}\n```{text}```')
        try:
            response_data = ujson.loads(text)
        except JSONDecodeError:
            self._logger.error('unable to decode: %s', text)
            return ErrorNode(msg=f'Unable to decode.\n```{text}```')

        if not response_data.get('ok'):
            self._logger.error('transfer is not ok: %s', text)
            return ErrorNode(msg=f'Unable to transfer.\n```{text}```')

        request_user.balance -= request.amount
        request.is_payed = True
        await dbs.users.update_one({'_id': request_user.id},
                                   {'$set': request_user.dict()})
        await dbs.withdraw_requests.update_one({'_id': request.id},
                                               {'$set': request.dict()})

        with suppress(TelegramAPIError):
            await bot.send_message(
                chat_id=request_user.user_id,
                text=_('✅ Your withdrawal request has been processed.\n'
                       '{amount} 💎 sent to you wallet').format(amount=request.amount),
                reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                    TransitionButton(to_node='MainMenu', text='Main Menu').compile()
                ]])
            )

        return None


class WithdrawRules(Node):
    back_to = 'WithdrawDI'

    @property
    def title(self) -> str:
        return _('About withdrawals')

    async def text(self) -> str:
        return _('⚠ Withdrawals can take up to 24h\n'
                 '⚠ Minimum amount: 0.5 💎\n'
                 '⚠ Maximum amount: 1000 💎\n'
                 '⚠ You need to play at least 5 payed games to unlock withdrawals\n'
                 '⚠ You can still use your funds while withdrawal request is pending\n')


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

    async def text(self) -> str:
        return _('⚠ Your withdrawal request is being processed\n'
                 '⚠ Withdrawals can take up to 24h\n'
                 '⚠ Conversion rate: 1 💎 = 1 TON')

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        amount = to_decimal(self.props.data)
        if is_cq(update):
            self._logger.info('request withdraw: %s', amount)
        user = get_current_user()
        request = WR(user_id=user.user_id, amount=amount)
        await dbs.withdraw_requests.insert_one(request.dict())

        await bot.send_message(
            chat_id=config.operator_id,
            text=f'New withdrawal request\n'
                 f'User: {user}\n'
                 f'User balance: {user.balance}\n'
                 f'Amount:{request.amount}',
            reply_markup=types.InlineKeyboardMarkup(1, inline_keyboard=[[
                TransitionButton(to_node=ConfirmWithdrawalAdmin,
                                 props={'r': str(request.id)}).compile()
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
