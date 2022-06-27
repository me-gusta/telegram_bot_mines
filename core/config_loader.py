from decimal import Decimal

import ujson
from pydantic import BaseModel
import hashlib
import hmac
from core.constants import FILES_DIR


class DB(BaseModel):
    host: str
    db_name: str
    user: str
    password: str


class Wallet(BaseModel):
    min_deposit: Decimal
    max_deposit: Decimal
    min_withdraw: Decimal
    max_withdraw: Decimal


class Config(BaseModel):
    db: DB
    wallet: Wallet
    operator_id: int
    token: str
    crypto_pay_token: str
    webapp_url: str
    server_name: str

    dev_mode: bool
    debug: bool

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
