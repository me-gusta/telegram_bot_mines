from decimal import Decimal, ROUND_DOWN
from typing import Union


def to_decimal(n: Union[int, float, str, Decimal]) -> Decimal:
    if isinstance(n, Decimal):
        return n.quantize(Decimal('.01'), ROUND_DOWN)
    else:
        return Decimal(str(n)).quantize(Decimal('.01'), ROUND_DOWN)