from aiogram import types, Dispatcher
from aiogram.dispatcher.middlewares import BaseMiddleware

from core.logging_config import root_logger
from db.helpers import get_or_create_user


class GetUserMiddleware(BaseMiddleware):
    logger = root_logger.getChild('GetUserMiddleware')

    async def on_pre_process_update(self, update: types.Update, data: dict):
        if update.message:
            user_data = update.message.from_user
        elif update.callback_query:
            user_data = update.callback_query.from_user
        elif update.inline_query:
            user_data = update.inline_query.from_user
        else:
            self.logger.error('Cannot extract user.')
            raise ValueError('Cannot extract user.')

        user = await get_or_create_user(user_data)

        self.logger.info('')
        dp = Dispatcher.get_current()
        dp.current_user = user
        # state = dp.decode_state(user.state).__repr_name__()
        self.logger.info('====== user: %s; state: %s ======', user, user.state)