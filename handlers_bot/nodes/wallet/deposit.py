from decimal import Decimal
from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from core.config_loader import config
from core.constants import URL_ENG_GUIDE
from core.pure import to_decimal
from core.aiogram_nodes.node import Node, URLButton, Button
from handlers_bot.nodes.decimal_input import DecimalInput
from i18n import _


class DepositCryptoBot(Node):
    emoji = '🤖'
    menu_btn = True

    class Props(BaseModel):
        data: Decimal = to_decimal(0)

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if isinstance(self.data, float):
                self.data = to_decimal(self.data)

    @property
    def title(self) -> str:
        return _('Deposit via @CryptoBot')

    @property
    def text(self) -> str:
        return _('You are depositing {amount} TON to your wallet\n\n'
                 'To finish the payment:\n'
                 '1. Press "💳 Go to Payment"\n'
                 '2. Press "START"\n'
                 '3. Follow @CryptoBot instructions').format(amount=self.props.data)


    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if self.props.data > config.wallet.max_deposit or self.props.data < config.wallet.min_deposit:
            self._logger.warn(f'wrong input data %s', self.props.data)
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
        return _('⚠ Right now we only accept deposit via @CryptoBot\n'
                 '⚠ Conversion rate: 1 TON = 1 💎')

    @property
    def buttons(self) -> List[List[Button]]:
        buttons = super(CryptoBotDI, self).buttons

        buttons += [
            [URLButton(url=_(URL_ENG_GUIDE), text=_('ℹ How to use @CryptoBot'))]
        ]
        return buttons
