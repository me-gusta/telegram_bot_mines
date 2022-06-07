import datetime
from typing import Union

from aiogram import types
from sqlalchemy import and_

from bot import bot
from db.engine import session
from db.models import User, MinesGameSettings, MinesGame, MinesGameStatus


async def get_or_create_user(user_data: types.User, do_commit=True) -> User:
    try:
        user: User = session.query(User).filter(User.user_id == user_data.id).first()
        user.username = user_data.username
        user.first_name = user_data.first_name
        user.last_name = user_data.last_name
        user.last_active = datetime.datetime.now()
    except AttributeError:
        user = User(user_id=user_data.id,
                    username=user_data.username,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    language_code=user_data.language_code)
        mines_game_settings = MinesGameSettings(user=user)
        session.add(user)
        session.add(mines_game_settings)
    if do_commit:
        session.commit()
    return user


def get_running_mines_game(user: User) -> Union[MinesGame, None]:
    return session.query(MinesGame).filter(
        and_(MinesGame.user_id == user.id, MinesGame.status == MinesGameStatus.RUNNING)
    ).first()
