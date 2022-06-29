import asyncio
import threading
import traceback
from pathlib import Path
from typing import Type

from aiogram import Dispatcher, executor
from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotFound

import handlers_server.api_mines as api
from bot import bot
from core.aiogram_nodes.debug_whitelist_middleware import DebugWhitelistMiddleware
from core.aiogram_nodes.get_user_middleware import GetUserMiddleware
from core.config_loader import config
from core.constants import WEBHOOK_PATH, CRYPTO_PAY_WEBHOOK_PATH, BASE_DIR
from core.logging_config import root_logger
from db.engine import create_tables
from core.aiogram_nodes.node import Node
from core.aiogram_nodes.telegram_dispatcher import TelegramDispatcher
from handlers_bot.fallback import setup as setup_fallback
from handlers_bot.inline_queries import inline_query_referral
from handlers_server import webhooks
from i18n import i18n_middleware


def init_dispatcher() -> Dispatcher:
    async def error_handler(update, error):
        root_logger.error(''.join(traceback.format_exc()))
        return True

    dp = TelegramDispatcher(bot)
    Dispatcher.set_current(dp)
    dp.middleware.setup(GetUserMiddleware())
    dp.middleware.setup(i18n_middleware)
    dp.middleware.setup(DebugWhitelistMiddleware())
    dp.register_errors_handler(error_handler)

    def all_subclasses(cls: Type):
        def _all_subclasses(cls: Type):
            out = []
            for sub in cls.__subclasses__():
                out.append(sub)
                out.extend(_all_subclasses(sub))
            return out
        subclasses = list(set(_all_subclasses(cls)))
        subclasses.sort(key=lambda x: x.__name__)
        return subclasses

    def import_node_dir(dir: Path, parent: str):
        for path in dir.iterdir():
            if path.name.startswith('_'):
                continue
            if path.is_dir():
                import_node_dir(path, parent + '.' + path.name)
            else:
                string = f'from {parent} import {path.name}'[:-3:]
                root_logger.info('DYNAMIC IMPORT: %s', string)
                exec(string)

    import_node_dir(BASE_DIR / 'handlers_bot/nodes', 'handlers_bot.nodes')

    for node_cls in all_subclasses(Node):
        root_logger.info('init_dispatcher. connect %s', node_cls)
        node_cls().setup(dp)

    dp.register_inline_handler(inline_query_referral)
    setup_fallback(dp)
    if config.debug:
        root_logger.info('---------- DEBUG MODE IS ON ----------')
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
        # root_logger.warning(f'DUBUG MIDDLEWARE. {request.method}, {request.path}')
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

    async def startup_db(_: web.Application):
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

    aiohttp_app.router.add_route('POST', CRYPTO_PAY_WEBHOOK_PATH, webhooks.crypto_pay_webhook)

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
    if config.dev_mode:
        root_logger.info('--- DEV MODE ---')
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
