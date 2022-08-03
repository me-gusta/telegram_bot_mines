from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, List, Optional

from aiogram import types
from pymongo import ReturnDocument

from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import dbs
from db.models import User

logger = root_logger.getChild('db.helpers')


async def get_user_by_user_id(user_id: int) -> Optional[User]:
    if user_id == 0:
        return None
    raw = await dbs.users.find_one({'user_id': user_id})
    if raw:
        return User(**raw)
    return None


async def get_or_create_user(tg_user: types.User) -> User:
    update_data = tg_user.to_python()
    del update_data['id']
    del update_data['is_bot']
    update_data['last_active'] = datetime.now()
    db_user = await dbs.users.find_one_and_update({'user_id': tg_user.id},
                                                  {'$set': update_data},
                                                  return_document=ReturnDocument.AFTER)
    if db_user is None:
        logger.info('new user. adding to database')
        db_user = User.from_telegram(tg_user)
        await dbs.users.insert_one(db_user.dict())
        # mines_game_preference = MinesGamePreference(user_id=db_user.id)
        # await dbs.mines_pref.insert_one(mines_game_preference.dict())
    if isinstance(db_user, dict):
        db_user = User(**db_user)
    return db_user


async def user_referral_stats(user: User) -> Tuple[Decimal, Decimal, int]:
    referrals: List[User] = await dbs.users.find({'referrer_id': user.user_id}).to_list(None)
    active_referrals = [x for x in referrals if x.last_active >= datetime.now() - timedelta(days=7)]
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
