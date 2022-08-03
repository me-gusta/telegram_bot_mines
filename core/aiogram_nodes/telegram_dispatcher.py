import traceback
from typing import TypeVar, Type

from aiogram import Dispatcher, types

from db.models import User

T = TypeVar('T')


class TelegramDispatcher(Dispatcher):
    current_user: User = None

    def __init__(self, bot):
        self.connected_nodes = {}
        # self.trees = []
        super().__init__(bot)

    async def process_update(self, update: types.Update):
        try:
            await super(TelegramDispatcher, self).process_update(update)
        except Exception:
            traceback.print_exc()
            exit()

    @classmethod
    def get_current(cls: Type[T], no_error=True) -> T:
        return Dispatcher.get_current()

    @classmethod
    async def transition(cls, node_state: str):
        dp = Dispatcher.get_current()
        node = dp.connected_nodes[node_state]
        await node._dispatch(types.CallbackQuery.get_current())

    def get_state_by_name(self, search_for: str):
        for state, node in self.connected_nodes.items():
            if node.__repr_name__() == search_for:
                return state
        raise ValueError(f'Not found {search_for} in self')

    def decode_state(self, state: str) -> str:
        return self.connected_nodes.get(state)

    def is_connected(self, node):
        return node.__repr_name__() in self.connected_nodes.values()

    def connect(self, node):
        self.connected_nodes[node.state] = node

