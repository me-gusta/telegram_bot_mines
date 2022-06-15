from typing import TypeVar, Type

from aiogram import Dispatcher

from core.logging_config import root_logger
from db.models import User

T = TypeVar('T')


class TelegramDispatcher(Dispatcher):
    current_user: User = None

    def __init__(self, bot):
        self.connected_nodes = []
        super().__init__(bot)

    @classmethod
    def get_current_user(cls) -> User:
        # root_logger.info('Get current user')
        user = Dispatcher.get_current().current_user
        if user:
            return user
        root_logger.error('TelegramDispatcher.current_user is none')
        raise ValueError('user is none')
