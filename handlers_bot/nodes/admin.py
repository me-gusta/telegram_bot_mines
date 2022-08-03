from typing import List

from core.aiogram_nodes.node import Node, Button


class AdminMenu(Node):
    commands = ['admin']

    only_admin = True

    @property
    def title(self) -> str:
        return 'Admin Menu'

    async def text(self) -> str:
        msg = 'admin menu'
        return msg

    @property
    def buttons(self) -> List[List[Button]]:
        return [
        #     games
            # users

        ]


    # async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:

