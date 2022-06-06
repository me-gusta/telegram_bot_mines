from aiogram import Bot
from aiogram.bot.api import TelegramAPIServer

from core.config_loader import config


class TelegramAPIServerTest(TelegramAPIServer):
    @classmethod
    def make(cls) -> 'TelegramAPIServer':
        base = 'https://api.telegram.org'
        return cls(
            base=f"{base}/bot{{token}}/test/{{method}}",
            file=f"{base}/file/bot{{token}}/test/{{path}}",
        )


if config.dev_mode:
    bot = Bot(token=config.token, server=TelegramAPIServerTest.make())
else:
    bot = Bot(token=config.token)#, server=TelegramAPIServerTest.make())

Bot.set_current(bot)
