import base64
import binascii
from typing import Any

import ujson
from aiogram import types, Dispatcher

from core.logging_config import root_logger
from db.models import User


def encode_callback_data(data: dict) -> str:
    out = base64.b64encode(ujson.dumps(data).encode('utf-8')).decode('utf-8')
    if len(out) > 64:
        raise ValueError('Too much callback data =)')
    return out


def decode_callback_data(encoded: str) -> dict:
    try:
        out = ujson.loads(base64.b64decode(encoded))
    except (ujson.JSONDecodeError, binascii.Error):
        return {}
    return out


def is_msg(update: Any):
    return isinstance(update, types.Message)


def is_cq(update: Any):
    return isinstance(update, types.CallbackQuery)


def get_current_user() -> User:
    user = Dispatcher.get_current().current_user
    if user:
        return user
    root_logger.error('TelegramDispatcher.current_user is none')
    raise ValueError('user is none')