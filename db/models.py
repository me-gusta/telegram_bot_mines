import base64
import binascii
import datetime
import enum
import random
from decimal import Decimal, ROUND_DOWN
from functools import cached_property
from typing import List, Union

import ujson
from sqlalchemy import Column, BigInteger, String, ForeignKey, DECIMAL, Enum, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship, backref, declarative_base

Base = declarative_base()


class UserState:
    NONE = 'NONE'
    ON_DEPOSIT_AMOUNT = 'ON_DEPOSIT_AMOUNT-'
    ON_WITHDRAW_AMOUNT = 'ON_WITHDRAW_AMOUNT-'

    @staticmethod
    def on_deposit_amount(message_id: int) -> str:
        return UserState.ON_DEPOSIT_AMOUNT + str(message_id)

    @staticmethod
    def on_withdraw_amount(message_id: int) -> str:
        return UserState.ON_WITHDRAW_AMOUNT + str(message_id)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True)
    username = Column(String(32), default='')
    first_name = Column(String(64), default='')
    last_name = Column(String(64), default='')
    language_code = Column(String(10), default='en')

    state = Column(String(64), default=UserState.NONE)
    menu_message_id = Column(BigInteger, default=0)

    last_active = Column(DateTime(), default=datetime.datetime.now)

    balance = Column(DECIMAL, default=0)

    referrer_user_id = Column(BigInteger, default=0)
    referral_count = Column(Integer, default=0)
    referral_balance = Column(DECIMAL, default=0)

    def __repr__(self):
        if self.username:
            return f'<User {self.id} @{self.username}>'
        else:
            return f'<User {self.id}>'

    def change_balance(self, n: Union[float, Decimal]):
        value = Decimal(str(n)) if isinstance(n, float) else n
        total = Decimal(str(self.balance)) + value
        total = total.quantize(Decimal('.01'), rounding=ROUND_DOWN)
        self.balance = total

    @property
    def ref(self):
        return base64.b64encode(str(self.user_id).encode('utf-8')).decode('utf-8').replace('=', '')

    @staticmethod
    def ref_decode(ref: str) -> int:
        if ref == '':
            return 0
        try:
            return int(base64.b64decode(ref + '==='))
        except (binascii.Error, ValueError):
            return 0

    @property
    def referral_share(self) -> Decimal:
        if self.referral_count >= 500:
            return Decimal(6)
        elif self.referral_count >= 100:
            return Decimal(5)
        elif self.referral_count >= 25:
            return Decimal(4)
        return Decimal(3)



class MinesGameSettings(Base):
    __tablename__ = 'mines_game_settings'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref=backref('mines_game_settings', uselist=False))
    last_bet = Column(DECIMAL, default=1)
    last_mines = Column(Integer, default=1)

    def __str__(self) -> str:
        return f'<MGS {self.last_bet}>'

    def dict(self):
        return {'last_bet': self.last_bet, 'last_mines': self.last_mines}


class MinesGameStatus(enum.Enum):
    WON = 'won'
    LOST = 'lost'
    RUNNING = 'running'
    CASHOUT = 'cashout'


class MinesGame(Base):
    __tablename__ = 'mines_game'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User')
    bet = Column(DECIMAL)
    check_string = Column(String(255))
    hash = Column(String(255))
    mines_json = Column(String(255))
    revealed_json = Column(String(255), default='[]')
    status = Column(Enum(MinesGameStatus), default=MinesGameStatus.RUNNING)

    @cached_property
    def mines(self):
        return ujson.loads(self.mines_json)

    @property
    def revealed(self):
        if not hasattr(self, '_revealed'):
            self._revealed = ujson.loads(self.revealed_json)
        return self._revealed

    def set_revealed(self, revealed: List[int]):
        if hasattr(self, '_revealed'):
            del self._revealed
        self.revealed_json = ujson.dumps(revealed)

    def __str__(self) -> str:
        return f'<Mines {self.id}>'


class Invoice(Base):
    __tablename__ = 'invoice'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User')
    amount = Column(DECIMAL)
    hash = Column(String(32))
    message_id = Column(Integer)
    is_payed = Column(Boolean, default=False)


class WithdrawRequest(Base):
    __tablename__ = 'withdraw_request'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User')
    amount = Column(DECIMAL)
    is_payed = Column(Boolean, default=False)
    date = Column(DateTime(), default=datetime.datetime.now)
    spend_id = Column(String, default=random.randbytes(8).hex())
