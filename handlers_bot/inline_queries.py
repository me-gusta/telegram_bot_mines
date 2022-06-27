from aiogram import types

from core.aiogram_nodes.util import get_current_user
from i18n import _


async def inline_query_referral(query: types.InlineQuery):
    user = get_current_user()
    text = _('🍀 Try your luck and win TON with me!\n') + 'https://t.me/LuckyTonBot?start=' + user.ref
    print(text)
    results = [
        types.InlineQueryResultArticle(
            id='result',
            title=_('Invite Friend'),
            input_message_content=types.InputMessageContent(message_text=text),
            thumb_url='https://bot-frontend-demo.web.app/img/other/refer.png'
        )
    ]
    await query.answer(results, cache_time=1)
