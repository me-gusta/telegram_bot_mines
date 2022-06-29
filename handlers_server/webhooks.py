import logging
from contextlib import suppress

import ujson
from aiogram import Dispatcher, types
from aiogram.utils.exceptions import MessageNotModified, TelegramAPIError
from aiohttp import web
from aiohttp.web_response import Response

from bot import bot
from core.aiogram_nodes.node import TransitionButton
from core.config_loader import config
from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import session
from db.models import Invoice
from handlers_bot.nodes.games import Games
from handlers_bot.nodes.main_menu import MainMenu
from i18n import _

async def telegram_webhook(request: web.Request):
    update_text = await request.text()
    logging.info('New update')
    dp: Dispatcher = request.app['dp']
    await dp.process_updates([types.Update(**ujson.loads(update_text))])
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
        [TransitionButton(to_node=MainMenu).compile()],
        [TransitionButton(to_node=Games).compile()]
    ]

    invoice.is_payed = True
    amount = to_decimal(invoice.amount)
    admin_bonus_text = ''
    if invoice.user.deposit_bonus:
        bonus = (amount / 100 * to_decimal(invoice.user.deposit_bonus))
        admin_bonus_text = f'\n\ndeposit bonus activated. User got {bonus} free TON'
        amount = amount
    invoice.user.balance += amount
    invoice.user.sum_deposit += invoice.amount
    session.commit()
    with suppress(TelegramAPIError):
        await bot.send_message(
                text=text,
                chat_id=invoice.user.user_id,
                parse_mode='markdown',
                reply_markup=types.InlineKeyboardMarkup(1, buttons),
            )
    await bot.send_message(config.operator_id,
                           text=f'DEPOSIT\n'
                                f'user: {invoice.user}\n'
                                f'amount: {invoice.amount}'
                                f'{admin_bonus_text}')
    return Response(text='ok')


