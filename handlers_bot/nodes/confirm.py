from typing import Any, List
from pydantic import BaseModel

from core.pure import to_decimal
from core.aiogram_nodes.node import Node, TransitionButton, Button
from i18n import _


class Confirm(Node):
    emoji = '✅'

    class Props(BaseModel):
        msg: str = 'continue'
        data: Any = ''
        next_state = ''

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if isinstance(self.data, float):
                self.data = to_decimal(self.data)

    @property
    def header(self) -> str:
        return self.emoji + ' ' + _('Confirmation')

    async def text(self) -> str:
        return _('Are you sure you want to {msg}?').format(msg=self.props.msg)

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [TransitionButton(text=self.emoji + ' ' + _('Confirm'),
                              props={'data': self.props.data},
                              to_node=self.props.next_state)]
        ]
