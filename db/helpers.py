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
    del update_data['language_code']
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


async def user_referral_stats(user: User) -> Tuple[int, Decimal, int]:
    referrals: List[dict] = await dbs.users.find({'referrer_user_id': user.user_id}).to_list(None)
    total_revenue = to_decimal(sum([x.get('sum_revenue') for x in referrals if x.get('sum_revenue')]))
    share = 25

    if total_revenue > 50000:
        share = 90
    elif total_revenue > 10000:
        share = 80
    elif total_revenue > 5000:
        share = 60
    elif total_revenue > 1000:
        share = 45
    elif total_revenue > 200:
        share = 35

    return share, total_revenue, len(referrals)
