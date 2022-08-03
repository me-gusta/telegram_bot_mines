from decimal import Decimal
from typing import List

import ujson
from pydantic import BaseModel
import hashlib
import hmac
from core.constants import FILES_DIR


class Wallet(BaseModel):
    min_deposit: Decimal
    max_deposit: Decimal
    min_withdraw: Decimal
    max_withdraw: Decimal


class Game(BaseModel):
    min_bet: Decimal
    max_bet: Decimal

class WebApps(BaseModel):
    mines: str

class Config(BaseModel):
    mongodb: str
    wallet: Wallet
    webapps: WebApps
    game: Game
    operator_id: int
    token: str
    crypto_pay_token: str
    server_name: str

    dev_mode: bool
    debug: bool

    referral_deposit_bonus: int
    debug_whitelist: List[int] = list()

    secret: bytes = b''

    def __init__(self, **data):
        super().__init__(**data)
        self.secret = hmac.new("WebAppData".encode(), self.token.encode(), hashlib.sha256).digest()


def load_config() -> Config:
    with open(FILES_DIR / 'config.json', 'r', encoding='utf-8') as f:
        config = Config(**ujson.loads(f.read()))
    if config.dev_mode:
        with open(FILES_DIR / 'config_dev.json', 'r', encoding='utf-8') as f:
            config = Config(**ujson.loads(f.read()))
    return config


config: Config = load_config()
