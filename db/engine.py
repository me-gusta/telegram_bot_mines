from dataclasses import dataclass

import motor.motor_asyncio
from motor.core import AgnosticCollection

from core.config_loader import config
from db.codecs import codec_options

database = motor.motor_asyncio.AsyncIOMotorClient(config.mongodb).luckyton


@dataclass
class Databases:
    users: AgnosticCollection
    mines_pref: AgnosticCollection
    withdraw_requests: AgnosticCollection
    invoices: AgnosticCollection


dbs = Databases(
    users=database.get_collection("users", codec_options=codec_options),
    mines_pref=database.get_collection("mines_game_preference", codec_options=codec_options),
    withdraw_requests=database.get_collection("withdraw_requests", codec_options=codec_options),
    invoices=database.get_collection("invoices", codec_options=codec_options),
)
