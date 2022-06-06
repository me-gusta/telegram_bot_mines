import logging

import ujson
from aiogram import Dispatcher, types
from aiohttp import web
from aiohttp.web_response import Response

from core.logging_config import root_logger


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
    if update['update_type'] != 'invoice_paid':
        return Response(text='not ok')
    return Response(text='ok')


