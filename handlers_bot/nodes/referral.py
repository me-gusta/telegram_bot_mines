from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from bot import bot
from core.config_loader import config
from core.constants import URL_SUPPORT
from core.aiogram_nodes.node import Node, Button, TransitionButton, URLButton
from core.aiogram_nodes.util import get_current_user
from core.pure import to_decimal
from db.helpers import user_referral_stats
from i18n import _


class ReferralRules(Node):
    emoji = 'ℹ'
    back_to = 'Referral'

    @property
    def title(self) -> str:
        return _('Referral Program Rules')

    async def text(self) -> str:
        return _('Invite your friends and earn up to *90%* of our revenue from bets placed by them!\n'
                 'Your referrals will get +10% to their first deposit.\n\n') + _(
            'The more people use your invite code, the more percent of revenue you will get.\n'
            '25% — Net revenue 0-200 TON\n'
            '35% — Net revenue 201-1000 TON\n'
            '45% — Net revenue 1001-5000 TON\n'
            '60% — Net revenue 5001-10000 TON\n'
            '80% — Net revenue 10001-50001 TON\n'
            '90% — Net revenue 50001 TON or more\n'
            '_Cheating, botting and other malicious actions related to the referral system would not be tolerated._\n\n'
            'If you are a content maker and have a large audience get in touch with us. '
            'We can discuss special referral program with a bigger share') + '\n\n' + _(
            'Earn 0.5 TON for free! Simply post a review about LuckyTON in any social media and send proof to our support.'
        )

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

    async def text(self) -> str:
        msg = self.props.error_msg or _(
            '⚠ Your withdrawal request is being processed\n'
            '⚠ Withdrawals can take up to 24h\n'
            '⚠ Conversion rate: 1 💎 = 1 TON')
        return msg

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        user = get_current_user()
        share, total_revenue, count = await user_referral_stats(user)
        referral_balance = to_decimal(total_revenue * to_decimal(share / 100))
        if referral_balance <= config.wallet.min_withdraw:
            self.props.error_msg = '❌ ' + _('Nothing to withdraw')
            return
        await bot.send_message(
            chat_id=config.operator_id,
            text=f'Кто-то захотел вывести реферальные деньги.\n'
                 f'Нужно как-то это решать......\n'
                 f'вперед, автоматика :)))\n\n'
                 f'user id: {user.user_id}\n'
                 f'total revenue: {total_revenue}\n'
                 f'amount referrals: {count}\n'
                 f'referral_balance: {referral_balance}')
        return


class Referral(Node):
    emoji = '🤝'
    commands = ['referral']
    back_to = 'MainMenu'

    @property
    def title(self) -> str:
        return _('Referral Program')

    async def text(self) -> str:
        user = get_current_user()
        share, total_revenue, count = await user_referral_stats(user)
        referral_balance = to_decimal(total_revenue * to_decimal(share / 100))

        return _('Invite your friends and earn up to *90%* of our revenue from bets placed by them!\n'
                 'Your referrals will get +10% to their first deposit.\n\n') + _(
                 'Your share: {share}%\n'
                 'Referrals: {count}\n'
                 'Net revenue: {total_revenue}\n'
                 'Total income: {balance} 💎\n\n'
                 'Invite link: `https://t.me/LuckyTonBot?start={ref}`').format(ref=user.ref,
                                                                               count=count,
                                                                               total_revenue=total_revenue,
                                                                               share=share,
                                                                               balance=referral_balance)

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [ReferralButton(user_name=get_current_user().first_name)],

            [TransitionButton(to_node=ReferralWithdraw), TransitionButton(to_node=ReferralRules)]
        ]
