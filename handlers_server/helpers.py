import hashlib
import hmac
from typing import Any, Union
from urllib.parse import unquote

import ujson
from aiogram import types
from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from pydantic import BaseModel, ValidationError

from core import constants
from core.config_loader import config
from core.logging_config import root_logger
from db.helpers import get_or_create_user
from db.models import User


def validate_telegram_string(raw_string: str, do_commit=True) -> User:
    data_check_string = unquote(raw_string)
    data_check_arr = data_check_string.split('&')
    data_check_arr.sort()
    frontend_hash = data_check_arr[1].removeprefix('hash=')
    del data_check_arr[1]

    data_check_string = "\n".join(data_check_arr)

    calculated_hash = hmac.new(config.secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if calculated_hash != frontend_hash:
        raise HTTPBadRequest(text='Validation Failed')
    else:
        user_data = ujson.loads(data_check_arr[-1].removeprefix('user='))
        user = get_or_create_user(types.User(**user_data), do_commit)
        return user


class ApiView(web.View):
    logger = root_logger.getChild('ApiView')

    class PostParams(BaseModel):
        any: Any

    async def retrieve_post_params(self, request: Request) -> Any:
        post_data = await request.post()
        try:
            data = post_data
            return self.PostParams(**data)
        except ValidationError as e:
            self.logger.error(f'Incorrect payload. Received post: {post_data}. Expecting: {self.PostParams}')
            raise HTTPBadRequest(text='Incorrect payload')

    async def retrieve_fetch_params(self, request: Request) -> Any:
        text = await request.text()
        try:
            data = ujson.loads(text)
            return self.PostParams(**data)
        except ValidationError as e:
            self.logger.error(f'Incorrect payload. Received text: {text}')
            raise HTTPBadRequest(text='Incorrect payload')

    def json_response(self, data: dict):
        response = web.Response()
        response.content_type = 'application/json'
        response.charset = 'utf-8'
        response.body = ujson.dumps(data)
        return response

    async def options(self):
        return Response(text='ok')
