from aiogram import types, Dispatcher
from aiogram.dispatcher.middlewares import BaseMiddleware


from bot import bot
from core.aiogram_nodes.util import get_current_user
from core.config_loader import config
from core.logging_config import root_logger
from db.helpers import get_or_create_user
from i18n import _

class DebugWhitelistMiddleware(BaseMiddleware):
    logger = root_logger.getChild('DebugWhitelistMiddleware')

    async def on_pre_process_update(self, update: types.Update, data: dict):
        user = get_current_user()
        if config.debug and user.user_id not in config.debug_whitelist:
            await bot.send_message(
                chat_id=user.user_id,
                text=_('🆕 We are updating the bot now.\n'
                       '⏰ Please try again later.\n'
                       '🙏🏻 Sorry for inconvenience.\n\n'
                       'Use this command to open the menu 👉🏻 /menu')
            )
            raise ValueError('Bot in debug mode. User rejected')

        dp = Dispatcher.get_current()
        dp.current_user = user
