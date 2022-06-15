import datetime
from contextlib import suppress
from typing import Union

from aiogram import types
from sqlalchemy import and_

from bot import bot
from core.config_loader import config
from core.logging_config import root_logger
from db.engine import session
from db.models import User, MinesGameSettings, MinesGame, MinesGameStatus


async def get_or_create_user(user_data: types.User, do_commit=True, referrer_user_id: int = 0) -> User:
    try:
        user: User = session.query(User).filter(User.user_id == user_data.id).first()
        user.username = user_data.username
        user.first_name = user_data.first_name
        user.last_name = user_data.last_name
        user.last_active = datetime.datetime.now()
    except AttributeError:
        root_logger.info('new user. adding to database')
        user = User(user_id=user_data.id,
                    username=user_data.username,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    language_code=user_data.language_code,
                    referrer_user_id=referrer_user_id)
        referrer: Union[User, None] = None
        if referrer_user_id:
            referrer = session.query(User).filter(User.user_id == referrer_user_id).first()
            if referrer:
                root_logger.info(f'new user. adding referrer, {referrer}')
                referrer.referral_count += 1
        mines_game_settings = MinesGameSettings(user=user)
        session.add(user)
        session.add(mines_game_settings)
        with suppress(Exception):
            await bot.send_message(chat_id=config.operator_id, text=f'New User\n'
                                                                    f'user: {user}\n'
                                                                    f'date: {datetime.datetime.now()}\n'
                                                                    f'referrer: {referrer if referrer else referrer_user_id}')

    if do_commit:
        session.commit()
    return user


def get_running_mines_game(user: User) -> Union[MinesGame, None]:
    return session.query(MinesGame).filter(
        and_(MinesGame.user_id == user.id, MinesGame.status == MinesGameStatus.RUNNING)
    ).first()
