from aiogram import types, Dispatcher

from core.constants import SUPPORT_USERNAME
from db.helpers import get_or_create_user
from handlers_bot.common import MenuCQ, answer_query, ReferralCQ
from i18n import _


async def referral(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user)
    text = _('🤑 Referral Program\n\n'
             'Invite your friends and earn up to *15%* of all their winning and losing bets!\n\n'
             'Your share: {share}%\n'
             'Invited: {count}\n'
             'Total income: {balance} 💎\n\n'
             'Invite link: `https://t.me/LuckyTonBot?start={ref}`').format(ref=user.ref,
                                                                           count=user.referral_count,
                                                                           share=user.referral_share,
                                                                           balance=user.referral_balance)
    buttons = [
        [types.InlineKeyboardButton('🤝 ' + _('Invite a friend'), switch_inline_query='invite')],
        [types.InlineKeyboardButton('ℹ ' + _('Rules'), callback_data=ReferralCQ.INFO)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=MenuCQ.MENU)]
    ]
    await answer_query(query, text, buttons)


async def info(query: types.CallbackQuery):
    text = _('ℹ Referral program rules\n\n'
             'Invite your friends and earn up to *15%* of their bets!\n\n'
             '• Starting share: 3%\n'
             '• 25 invitations: 4%\n'
             '• 100 invitations: 5%\n'
             '• 500 invitations: 6%\n\n'
             'If you are a content maker and have a large audience get in touch with us. '
             'We can discuss special referral program with a bigger share up to 15%')
    buttons = [
        [types.InlineKeyboardButton('✉ ' + _('Contact Us'), url='https://t.me/' + SUPPORT_USERNAME)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=ReferralCQ.REFERRAL)]
    ]
    await answer_query(query, text, buttons)


async def inline(query: types.InlineQuery):
    user = await get_or_create_user(query.from_user)
    text = _('🍀 Try your luck and win TON with me!\n') + 'https://t.me/LuckyTonBot?start=' + user.ref
    results = [
        types.InlineQueryResultArticle(
            id='result',
            title='Invite Friend',
            input_message_content=types.InputMessageContent(message_text=text),
            thumb_url='https://bot-frontend-demo.web.app/img/other/refer.png'
        )
    ]
    await query.answer(results)


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(referral, lambda call: call.data == ReferralCQ.REFERRAL)
    dp.register_callback_query_handler(info, lambda call: call.data == ReferralCQ.INFO)
    dp.register_inline_handler(inline, lambda call: call.query == 'invite')
