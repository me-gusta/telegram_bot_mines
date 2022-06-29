from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from bot import bot
from core.config_loader import config
from core.constants import URL_SUPPORT
from core.aiogram_nodes.node import Node, Button, TransitionButton, URLButton
from core.aiogram_nodes.util import get_current_user
from db.helpers import user_referral_stats
from i18n import _


class ReferralRules(Node):
    emoji = 'ℹ'
    back_to = 'Referral'

    @property
    def title(self) -> str:
        return _('Referral Program Rules')

    @property
    def text(self) -> str:
        return _('Invite your friends and earn up to *15%* of their bets! '
                 'Your referrals will get +10% to their first first deposit.\n\n'
                 'The more people use your invite code, the more percent from their bets you will get.\n'
                 '3% — Referral deposit 0-50 TON + 5 active referrals\n'
                 '4% — Referral deposit 50-125 TON + 15 active referrals\n'
                 '5% — Referral deposit 125-225 TON + 20 active referrals\n'
                 '6% — Referral deposit 225-350 TON + 25 active referrals\n'
                 '7% — Referral deposit 350-500 TON + 30 active referrals\n'
                 '8% — Referral deposit 500-700 TON + 30 active referrals\n'
                 '9% — Referral deposit 700-1000 TON + 30 active referrals\n'
                 '10% — Referral deposit 1000-2000 TON + 30 active referrals\n'
                 '_Active referral is someone who plays at least once a week_\n\n'
                 'If you are a content maker and have a large audience get in touch with us. '
                 'We can discuss special referral program with a bigger share up to 15%')

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [URLButton(url=URL_SUPPORT, text='✉ ' + _('Contact Us'))]
        ]


class ReferralButton(Button):
    user_name: str

    def __init__(self, user_name: str):
        self.user_name = user_name

    def compile(self) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton('🤝 ' + _('Invite a friend'),
                                          switch_inline_query='invite from ' + self.user_name)


class ReferralWithdraw(Node):
    emoji = '💎'
    back_to = 'Referral'

    class Props(BaseModel):
        error_msg: str = ''

    @property
    def title(self) -> str:
        return _('Withdraw')

    @property
    def text(self) -> str:
        msg = self.props.error_msg or _(
            '⚠ Your withdrawal request is being processed\n'
            '⚠ Withdrawals can take up to 24h\n'
            '⚠ Conversion rate: 1 💎 = 1 TON')
        return msg

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        user = get_current_user()
        share, sum_deposit, count = user_referral_stats(user)
        if user.referral_balance <= 0:
            self.props.error_msg = '❌ ' + _('Nothing to withdraw')
            return
        if count < 5:
            self.props.error_msg = '❌ ' + _(
                'You can not withdraw your referrals balance until you invite 5 active referrals.')
            return
        await bot.send_message(
            chat_id=config.operator_id,
            text=f'Кто-то захотел вывести реферальные деньги.\n'
                 f'Нужно как-то это решать......\n'
                 f'вперед, автоматика)))\n'
                 f'sum_deposit: {sum_deposit}\n\n'
                 f'ref count: {count}')
        return


class Referral(Node):
    emoji = '🤝'
    commands = ['referral']
    back_to = 'MainMenu'

    @property
    def title(self) -> str:
        return _('Referral Program')

    @property
    def text(self) -> str:
        user = get_current_user()
        share, sum_deposit, count = user_referral_stats(user)

        return _('Invite your friends and earn up to *15%* of all their winning and losing bets! '
                 'Your referrals will get +10% to their first first deposit.\n\n'
                 'Your share: {share}%\n'
                 'Active referrals: {count}\n'
                 'Referrals deposit: {sum_deposit}\n'
                 'Total income: {balance} 💎\n\n'
                 'Invite link: `https://t.me/LuckyTonBot?start={ref}`').format(ref=user.ref,
                                                                               count=count,
                                                                               sum_deposit=sum_deposit,
                                                                               share=share,
                                                                               balance=user.referral_balance)

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [ReferralButton(user_name=get_current_user().first_name)],

            [TransitionButton(to_node=ReferralWithdraw), TransitionButton(to_node=ReferralRules)]
        ]
