import asyncio
import threading
import traceback

from aiogram import Dispatcher, executor
from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotFound

import handlers_server.api_mines as api
from bot import bot
from core.config_loader import config
from core.constants import WEBHOOK_PATH, CRYPTO_PAY_WEBHOOK_PATH
from core.logging_config import root_logger
from db.engine import create_tables
from handlers_bot.callbacks.callbacks import setup as setup_callbacks
from handlers_server import webhooks
from i18n import i18n_middleware
from handlers_bot.commands import send_welcome


def init_dispatcher() -> Dispatcher:
    async def error_handler(update, error):
        root_logger.error(''.join(traceback.format_exc()))
        return True

    dp = Dispatcher(bot)
    dp.middleware.setup(i18n_middleware)
    dp.register_message_handler(send_welcome, commands=['start'])
    dp.register_errors_handler(error_handler)
    setup_callbacks(dp)
    return dp


def make_app(init_bot=False):
    @web.middleware
    async def cors_middleware(request: web.Request, handler):
        response = await handler(request)
        if request.headers.get('Origin') == 'http://127.0.0.1:8080' or \
                request.headers.get('Origin') == 'https://bot-frontend-demo.web.app':
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    @web.middleware
    async def debug_middleware(request: web.Request, handler):
        root_logger.warning(f'DUBUG MIDDLEWARE. {request.method}, {request.path}')
        try:
            response = await handler(request)
            return response
        except HTTPNotFound:
            root_logger.error(f'HTTPNotFound 404')
        except Exception:
            root_logger.error(''.join(traceback.format_exc()))
        return HTTPBadRequest(text='Something is wrong')

    async def startup_telegram_bot(app: web.Application):
        root_logger.info('Initializing bot')
        dp = init_dispatcher()
        app['dp'] = dp
        try:
            await dp.bot.delete_webhook(drop_pending_updates=True)

            await dp.bot.set_webhook(config.server_name + WEBHOOK_PATH)
        except Exception:
            root_logger.error(''.join(traceback.format_exc()))

    async def shutdown_telegram_bot(app: web.Application):
        root_logger.warning('Shutting down..')

        dp = app['dp']

        # Remove webhook (not acceptable in some cases)
        await bot.bot.delete_webhook()

        # Close DB connection (if used)
        await dp.storage.close()
        await dp.storage.wait_closed()

        root_logger.warning('Bye!')

    async def startup_db(app: web.Application):
        root_logger.info('Initializing database')
        await create_tables()

    aiohttp_app = web.Application(middlewares=[cors_middleware])
    if config.debug:
        aiohttp_app.middlewares.insert(0, debug_middleware)

    aiohttp_app.on_startup.append(startup_db)

    if init_bot:
        aiohttp_app.router.add_route('POST', WEBHOOK_PATH, webhooks.telegram_webhook)

        aiohttp_app.on_startup.append(startup_telegram_bot)
        aiohttp_app.on_shutdown.append(shutdown_telegram_bot)

    root_logger.info('Initializing routes')

    aiohttp_app.router.add_route('GET', CRYPTO_PAY_WEBHOOK_PATH, webhooks.crypto_pay_webhook)

    aiohttp_app.router.add_route('GET', '/test', api.index)

    aiohttp_app.router.add_route('POST', '/getUser', api.GetUserApi)
    aiohttp_app.router.add_route('OPTIONS', '/getUser', api.GetUserApi)

    aiohttp_app.router.add_route('POST', '/newGame', api.NewGameApi)
    aiohttp_app.router.add_route('OPTIONS', '/newGame', api.NewGameApi)

    aiohttp_app.router.add_route('POST', '/revealCell', api.RevealCellApi)
    aiohttp_app.router.add_route('OPTIONS', '/revealCell', api.RevealCellApi)

    aiohttp_app.router.add_route('POST', '/cashout', api.CashoutApi)
    aiohttp_app.router.add_route('OPTIONS', '/cashout', api.CashoutApi)

    return aiohttp_app


def run_polling():
    dp = init_dispatcher()

    def polling_thread(loop):
        asyncio.set_event_loop(loop)
        executor.start_polling(dp, skip_updates=True)

    def run_server_thread(loop):
        asyncio.set_event_loop(loop)
        web.run_app(make_app(init_bot=False), port=8855)

    loop = asyncio.get_event_loop()
    t1 = threading.Thread(target=polling_thread, args=(loop,))
    t2 = threading.Thread(target=run_server_thread, args=(loop,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


app = make_app(init_bot=True)

if __name__ == '__main__':
    run_polling()
