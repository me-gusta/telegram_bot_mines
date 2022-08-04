import logging
from contextlib import suppress

import ujson
from aiogram import Dispatcher, types
from aiogram.utils.exceptions import TelegramAPIError
from aiohttp import web
from aiohttp.web_response import Response

from bot import bot
from core.aiogram_nodes.node import TransitionButton
from core.config_loader import config
from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import dbs
from db.helpers import get_user_by_user_id
from db.models import Invoice
from handlers_bot.nodes.games import Games
from handlers_bot.nodes.main_menu import MainMenu
from i18n import _


async def telegram_webhook(request: web.Request):
    update_text = await request.text()
    logging.info('=== New update ===')
    dp: Dispatcher = request.app['dp']
    with suppress(Exception):
        await dp.process_updates([types.Update(**ujson.loads(update_text))])
    return Response(text='ok')


async def crypto_pay_webhook(request: web.Request):
    update_text = await request.text()
    root_logger.info(f'crypto_pay_webhook; {update_text=}')
    update = ujson.loads(update_text)
    if update.get('update_type') != 'invoice_paid' or update['payload'].get('status') != 'paid':
        return Response(text='not ok')
    invoice_hash = update['payload']['hash']
    invoice_query = await dbs.invoices.find_one({'hash': invoice_hash})
    if invoice_query is None:
        return Response(text='ok')

    invoice = Invoice(**invoice_query)
    invoice_user = await get_user_by_user_id(invoice.user_id)

    root_logger.info(f'crypto_pay_webhook; {invoice=}')
    if invoice.is_payed:
        return Response(text='ok')
    if not invoice_user:
        root_logger.error('user not found')
        return Response(text='ok')

    buttons = [
        [TransitionButton(to_node=MainMenu).compile()],
        [TransitionButton(to_node=Games).compile()]
    ]

    invoice.is_payed = True
    amount = to_decimal(invoice.amount)
    admin_bonus_text = ''
    if invoice_user.deposit_bonus:
        bonus = (amount / 100 * to_decimal(invoice_user.deposit_bonus))
        admin_bonus_text = f'\n\ndeposit bonus activated. User got {bonus} free TON'
        amount += bonus
        invoice_user.deposit_bonus = to_decimal(0)

    invoice_user.balance += amount
    invoice_user.sum_deposit += invoice.amount

    await dbs.users.update_one({'_id': invoice_user.id}, {'$set': invoice_user.dict()})

    await dbs.invoices.update_one({'_id': invoice.id}, {'$set': invoice.dict()})

    text = _('You deposited {amount} 💎 to you wallet!\n\n').format(amount=amount)
    with suppress(TelegramAPIError):
        await bot.send_message(
            text=text,
            chat_id=invoice_user.user_id,
            parse_mode='markdown',
            reply_markup=types.InlineKeyboardMarkup(1, buttons),
        )
        await bot.send_message(config.operator_id,
                               text=f'DEPOSIT\n'
                                    f'user: {invoice_user}\n'
                                    f'amount: {invoice.amount}'
                                    f'{admin_bonus_text}')
    return Response(text='ok')
