from typing import List, Union

from aiogram import types
from pydantic import BaseModel

from core.config_loader import config
from core.aiogram_nodes.node import Node, Button, TransitionButton, URLButton, NullNode
from core.aiogram_nodes.util import is_cq

from i18n import _


class Games(Node):
    emoji: str = '🕹'
    back_to = 'MainMenu'

    class Props(BaseModel):
        show_alert: int = 0

    @property
    def title(self) -> str:
        return _('Games')

    @property
    def footer(self) -> str:
        return _('Choose a Game')

    @property
    def text(self) -> str:
        return _('💣 *Mines*: Uncover all diamonds to maximize your profit!\n'
                 '💸 *Coinflip*: _[soon]_ Simple 50-50 game of chance.\n'
                 '🚀 *Rocket Launch*: _[soon]_ Hop on a starship and earn up to x10000!\n\n'
                 '_You can play every game for free if you set your bet to 0_')

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [URLButton(text='💣 ' + _('Mines'), url=config.webapp_url, is_webapp=True)],
            [TransitionButton(to_node=Games, props={'show_alert': 1}, text='💸 ' + _('Coinflip'))],
            [TransitionButton(to_node=Games, props={'show_alert': 2}, text='🚀 ' + _('Rocket Launch'))]
        ]

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if is_cq(update):
            if self.props.show_alert:
                if self.props.show_alert == 1:
                    await update.answer(
                        text=_('This game is still in development. Subscribe to our 📰 News to get notified!'),
                        show_alert=True)
                elif self.props.show_alert == 2:
                    await update.answer(
                        text=_('This game is still in development. Subscribe to our 📰 News to get notified!'),
                        show_alert=True)
                return NullNode()
