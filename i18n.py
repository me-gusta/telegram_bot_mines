from typing import Tuple, Any, Optional

from aiogram import types
from aiogram.contrib.middlewares.i18n import I18nMiddleware

from core.constants import FILES_DIR
from db.engine import session
from db.models import User


class TranslateMiddleware(I18nMiddleware):
    async def get_user_locale(self, action: str, args: Tuple[Any]) -> Optional[str]:
        current = types.User.get_current()
        user: User = session.query(User).filter(User.user_id == current.id).first()
        if user:
            return user.language_code
        else:
            return current.language_code


i18n_middleware = TranslateMiddleware('mybot', FILES_DIR / 'locales')

_ = i18n_middleware.gettext
