from typing import List

from handlers_bot.node import Node
from i18n import _


class Games(Node):
    emoji: str = '🕹'
    back_btn = True

    @property
    def title(self) -> str:
        return _('Games')

    @property
    def footer(self) -> str:
        return _('Choose a Game')

    @property
    def message(self) -> str:
        return _('💣 *Mines*: Uncover all diamonds to maximize your profit!\n'
                 '💸 *Coinflip*: _[soon]_ Simple 50-50 game of chance.\n'
                 '🚀 *Rocket Launch*: _[soon]_ Hop on a starship and earn up to x10000!\n\n'
                 '_You can play every game for free if you set your bet to 0_')

    def buttons(self) -> List[List[Node]]:
        return [

        ]
