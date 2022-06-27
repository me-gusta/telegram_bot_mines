import logging
from contextlib import suppress

import ujson
from aiogram import Dispatcher, types
from aiogram.utils.exceptions import MessageNotModified
from aiohttp import web
from aiohttp.web_response import Response

from bot import bot
from core.config_loader import config
from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import session
from db.models import Invoice
from i18n import _

async def telegram_webhook(request: web.Request):
    update_text = await request.text()
    logging.info('New update')
    dp: Dispatcher = request.app['dp']
    await dp.process_update(types.Update(**ujson.loads(update_text)))
    return Response(text='ok')


async def crypto_pay_webhook(request: web.Request):
    update_text = await request.text()
    root_logger.info(f'crypto_pay_webhook; {update_text=}')
    update = ujson.loads(update_text)
    if update.get('update_type') != 'invoice_paid' or update['payload'].get('status') != 'paid':
        return Response(text='not ok')
    invoice: Invoice = session.query(Invoice).filter(Invoice.hash == update['payload']['hash']).first()
    root_logger.info(f'crypto_pay_webhook; {invoice=}')
    if invoice is None or invoice.is_payed:
        return Response(text='ok')

    text = _('You deposited {amount} 💎 to you wallet!\n\n').format(amount=invoice.amount)
    buttons = [
        [types.InlineKeyboardButton('🕹️ ' + _('Games'), callback_data='')],
        [types.InlineKeyboardButton(_('Back to Menu'), callback_data='MenuCQ.MENU')]
    ]

    invoice.is_payed = True
    invoice.user.balance += invoice.amount
    session.commit()
    with suppress(MessageNotModified):
        await bot.edit_message_text(
                text=text,
                chat_id=invoice.user.user_id,
                message_id=invoice.message_id,
                parse_mode='markdown',
                reply_markup=types.InlineKeyboardMarkup(1, buttons),
            )
    await bot.send_message(config.operator_id,
                           text=f'TOP UP\n'
                                f'user: {invoice.user}\n'
                                f'amount: {invoice.amount}')
    return Response(text='ok')


