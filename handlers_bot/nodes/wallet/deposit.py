import decimal
from decimal import Decimal
from typing import Union, List

import aiohttp
import ujson
from aiogram import types
from pydantic import BaseModel
from ujson import JSONDecodeError

from core.aiogram_nodes.util import get_current_user
from core.config_loader import config
from core.constants import URL_ENG_GUIDE, CRYPTO_PAY_URL
from core.pure import to_decimal
from core.aiogram_nodes.node import Node, URLButton, Button, NullNode, ErrorNode
from db.engine import dbs
from db.models import Invoice
from handlers_bot.nodes.decimal_input import DecimalInput
from i18n import _


class DepositCryptoBot(Node):
    emoji = '🤖'
    menu_btn = True

    class Props(BaseModel):
        data: Decimal = to_decimal(0)
        invoice_hash: str = ''

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if isinstance(self.data, float):
                self.data = to_decimal(self.data)

    @property
    def title(self) -> str:
        return _('Deposit via @CryptoBot')

    async def text(self) -> str:
        return _('You are depositing {amount} TON to your wallet\n\n'
                 'To finish the payment:\n'
                 '1. Press "💳 Go to Payment"\n'
                 '2. Press "START"\n'
                 '3. Follow @CryptoBot instructions').format(amount=self.props.data)

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [URLButton(url='https://t.me/CryptoBot?start=' + self.props.invoice_hash,
                       text='💳 ' + _('Go to Payment'))]
        ]

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        try:
            amount = to_decimal(self.props.data)
        except decimal.InvalidOperation:
            self._logger.warn(f'invalid input data %s', self.props.data)
            return NullNode()

        if amount > config.wallet.max_deposit or amount < config.wallet.min_deposit:
            self._logger.warn(f'invalid input amount %s', amount)
            return NullNode()
        headers = {
            'Crypto-Pay-API-Token': config.crypto_pay_token,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with aiohttp.ClientSession(headers=headers) as client_session:
            resp = await client_session.post(CRYPTO_PAY_URL + 'createInvoice',
                                             data={'asset': 'TON', 'amount': amount})
            if resp.status != 200:
                self._logger.error('response status %s', resp.status)
                return ErrorNode(msg='Unable to deposit...')
            text = await resp.text()
        try:
            invoice_dict = ujson.loads(text)
        except JSONDecodeError:
            self._logger.error('unable to decode: %s', text)
            return ErrorNode(msg='Unable to deposit...')

        if not invoice_dict.get('ok'):
            self._logger.error('invoice is not ok: %s', text)
            return ErrorNode(msg='Unable to deposit...')

        invoice = Invoice(user_id=get_current_user().user_id,
                          amount=amount,
                          hash=invoice_dict['result']['hash'])
        await dbs.invoices.insert_one(invoice.dict())
        self._logger.info('new deposit invoice: %s', invoice)
        self.props.invoice_hash = invoice.hash
        return None


class CryptoBotDI(DecimalInput):
    emoji = '💎'
    min = config.wallet.min_deposit
    max = config.wallet.max_deposit

    next_state = DepositCryptoBot.state()

    back_to = 'MainMenu'

    @property
    def title(self) -> str:
        return _('Deposit')

    @property
    def header(self) -> str:
        return '🤖' + ' ' + _('Deposit via @CryptoBot')

    @property
    def footer(self) -> str:
        return _('Please enter or choose the amount for deposit.')

    @property
    def confirm_msg(self) -> str:
        return _('deposit {amount} TON')

    @property
    def custom_text(self) -> str:
        msg = _('⚠ Right now we only accept deposit via @CryptoBot\n'
                '⚠ Conversion rate: 1 TON = 1 💎')
        return msg

    @property
    def buttons(self) -> List[List[Button]]:
        buttons = super(CryptoBotDI, self).buttons

        buttons += [
            [URLButton(url=_(URL_ENG_GUIDE), text=_('ℹ How to use @CryptoBot'))]
        ]
        return buttons
