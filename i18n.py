from typing import Tuple, Any, Optional

from aiogram.contrib.middlewares.i18n import I18nMiddleware

from core.constants import FILES_DIR
from handlers_bot.telegram_dispatcher import TelegramDispatcher


class TranslateMiddleware(I18nMiddleware):
    async def get_user_locale(self, action: str, args: Tuple[Any]) -> Optional[str]:
        user = TelegramDispatcher.get_current_user()
        return user.language_code

i18n_middleware = TranslateMiddleware('mybot', FILES_DIR / 'locales')

_ = i18n_middleware.gettext
