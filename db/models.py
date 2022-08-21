import asyncio
import base64
import binascii
import random
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Union, Optional

from aiogram import types
from bson import ObjectId
from pydantic import BaseModel, Field

from core.pure import to_decimal


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId value")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: int}
        use_enum_values = True

    def dict(self, *args, **kwargs):
        kwargs.setdefault('by_alias', True)
        return super(MongoModel, self).dict(*args, **kwargs)


class User(MongoModel):
    user_id: int
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    language_code: str = 'en'

    last_active: datetime = datetime.now()
    date_registered: datetime = datetime.now()

    balance: Decimal = to_decimal(0)
    deposit_bonus: Decimal = to_decimal(0)

    referrer_user_id: int = 0
    referral_balance: Decimal = to_decimal(0)

    sum_deposit: Decimal = to_decimal(0)
    sum_revenue: Decimal = to_decimal(0)

    state: str = 0
    menu_message_id: int = 0

    @classmethod
    def from_telegram(cls, u: types.User):
        data = u.to_python()
        data['user_id'] = data['id']
        del data['id']
        return cls(**data)

    def __str__(self):
        short_id = str(self.id)[-4::]
        if self.username:
            return f'<User {short_id} @{self.username}>'
        else:
            return f'<User {short_id} {self.full_name}>'

    @property
    def full_name(self):
        name = self.first_name
        if self.last_name:
            name += ' ' + self.last_name
        return name

    def change_balance(self, n: Union[float, Decimal]):
        value = to_decimal(n)
        total = self.balance + value
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


class MinesGamePreference(MongoModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: int
    last_bet: Decimal = 1
    last_mines: int = 1

    def __str__(self) -> str:
        return f'<MGS {self.id}>'


class Invoice(MongoModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: int
    amount: Decimal
    hash: str
    is_payed: bool = False

    def __repr__(self):
        return f'<Invoice {self.id} {self.amount}>'


class WithdrawRequest(MongoModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: int
    amount: Decimal
    is_payed: bool = False
    date: datetime = datetime.now()
    spend_id: str = random.randbytes(8).hex()

