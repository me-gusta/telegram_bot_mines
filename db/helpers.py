import datetime
from contextlib import suppress
from decimal import Decimal
from typing import Union, Tuple, List

from aiogram import types
from sqlalchemy import and_

from bot import bot
from core.config_loader import config
from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import session
from db.models import User, MinesGameSettings, MinesGame, MinesGameStatus


async def get_or_create_user(user_data: types.User,
                             do_commit=True) -> User:
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
                    language_code=user_data.language_code)
        mines_game_settings = MinesGameSettings(user=user)
        session.add(user)
        session.add(mines_game_settings)

    if do_commit:
        session.commit()
    return user


def get_running_mines_game(user: User) -> Union[MinesGame, None]:
    game: MinesGame = session.query(MinesGame).filter(
        and_(MinesGame.user_id == user.id, MinesGame.status == MinesGameStatus.RUNNING)
    ).first()
    if game:
        if game.date < datetime.datetime.now() - datetime.timedelta(minutes=5):
            game.status = MinesGameStatus.LOST
            session.commit()
            return None
    return game


def user_referral_stats(user) -> Tuple[Decimal, Decimal, int]:
    referrals: List[User] = session.query(User).filter(User.referrer_user_id == user.user_id).all()
    active_referrals = [x for x in referrals if x.last_active >= datetime.datetime.now() - datetime.timedelta(days=7)]
    sum_deposit = to_decimal(sum([x.sum_deposit for x in active_referrals]))
    count = len(active_referrals)
    share = 3

    if count >= 15:
        if sum_deposit > 50:
            share = 4

    if count >= 20:
        if sum_deposit > 125:
            share = 5
    if count >= 25:
        if sum_deposit > 225:
            share = 6

    if count >= 30:
        if sum_deposit > 1000:
            share = 10
        elif sum_deposit > 700:
            share = 9
        elif sum_deposit > 500:
            share = 8
        elif sum_deposit > 350:
            share = 7

    share = Decimal(share)
    return share, sum_deposit, count