import base64
from decimal import Decimal
from typing import Union

import ujson
from aiogram import types

from core.config_loader import config
from core.pure import to_decimal
from handlers_bot.node import Node, Link, is_cq, RenderProps
from handlers_bot.nodes.decimal_input import DecimalInput
from i18n import _


class CryptoBotDI(DecimalInput):
    emoji = '🤖'
    min = config.wallet.min_deposit
    max = config.wallet.max_deposit


    @property
    def title(self) -> str:
        return _('Deposit via @CryptoBot')

    children = [
        [Link(emoji='ℹ',
              custom_title=lambda: _('How to use @CryptoBot'),
              url=_(
                  'https://telegra.ph/How-to-top-up-the-balance-of-the-LuckyTonBot-gaming-bot-using-CryptoBot-06-09'))]]

    @property
    def custom_text(self) -> str:
        return _('Conversion rate: 1 TON = 1 💎')


class CryptoBotPay(Node):
    amount: Decimal = Decimal(0)

    print_header = False

    menu_btn = True

    @property
    def title(self) -> str:
        return _('Deposit via @CryptoBot')

    @property
    def message(self) -> str:
        return _('To finish the payment:\n'
                 '1. Press "💳 Go to Payment"\n'
                 '2. Press "START"\n'
                 '3. Follow @CryptoBot instructions')


    async def render(self, update: Union[types.CallbackQuery, types.Message]) -> RenderProps:
        if is_cq(update):
            data = ujson.loads(base64.b64decode(update.data))
            amount = to_decimal(data['d'])
            self.logger.info('request deposit: %s', amount)
            self.children = [
                [Link(emoji='💳',
                      custom_title=lambda : _('Go to Payment'),
                      url='https://t.me/big_xyu')]
            ]
        return RenderProps()


class Deposit(Node):
    emoji = '💳'
    commands = ['deposit']
    back_btn = True

    children = [
        [CryptoBotDI(
            next_node=lambda x: CryptoBotPay(amount=x),
            confirm_text = lambda: _('deposit {amount}')
        )]
    ]

    @property
    def title(self) -> str:
        return _('Deposit')

    @property
    def message(self) -> str:
        return _('_Your Balance_: {balance} 💎\n\n'
                 '⚠ Currently we are accepting Toncoin deposits only via @CryptoBot').format(
            welcome=_('hello'),
            balance=self.user.balance)


# DecimalInput(
#             emoji='🤖',
#             # title='@CryptoBot',
#             text=_('Conversion rate: 1 TON = 1 💎'),
#
#             min=config.wallet.min_deposit,
#             max=config.wallet.max_deposit,
#             confirm_text=_('deposit {amount}'),
#             next=lambda x: CryptoBotPay(amount=x),
#             variable_state='Deposit',
#             children=[[Link(emoji='ℹ',
#                             title=_('How to use @CryptoBot'),
#                             url=_(
#                                 'https://telegra.ph/How-to-top-up-the-balance-of-the-LuckyTonBot-gaming-bot-using-CryptoBot-06-09'))]])
