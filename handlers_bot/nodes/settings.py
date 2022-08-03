from typing import Union, List

from aiogram import types
from pydantic import BaseModel

from core.aiogram_nodes.node import Node, Button, TransitionButton
from core.aiogram_nodes.util import is_cq
from core.aiogram_nodes.util import get_current_user
from i18n import _


def get_flag(language_code: str) -> str:
    out = '🇬🇧'
    if language_code == 'ru':
        out = '🇷🇺'
    return out + ' '

def cycle_languages(language_code:str) -> str:
    if language_code == 'en':
        return 'ru'
    else:
        return 'en'



class Settings(Node):
    emoji = '⚙'
    commands = ['settings']
    back_to = 'MainMenu'

    class Props(BaseModel):
        lang: bool = False

    @property
    def title(self) -> str:
        return _('Settings')

    async def text(self) -> str:
        return _('You can customize bot settings here\n')

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [TransitionButton(to_node=Settings,
                              text=get_flag(get_current_user().language_code) + _('Change Language'),
                              props={'lang': True})]
        ]

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        if is_cq(update) and self.props.lang:
            user = get_current_user()
            user.language_code = cycle_languages(user.language_code)
        return
