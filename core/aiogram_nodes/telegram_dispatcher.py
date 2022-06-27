import binascii
import traceback
from typing import TypeVar, Type

import ujson
from aiogram import Dispatcher, types

from core.logging_config import root_logger
from db.models import User
from core.aiogram_nodes.util import decode_callback_data

T = TypeVar('T')


class TelegramDispatcher(Dispatcher):
    current_user: User = None

    def __init__(self, bot):
        self.connected_nodes = {}
        # self.trees = []
        super().__init__(bot)

    async def process_update(self, update: types.Update):
        if update.callback_query:
            root_logger.debug('decoded callback data %s', decode_callback_data(update.callback_query.data))
        await super(TelegramDispatcher, self).process_update(update)

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
        self.connected_nodes[node.state] = node  # .__repr_name__()
        # self.add_to_tree(node, node.ancestor)

    # def add_to_tree(self, node, ancestor):
    #     if not ancestor:
    #         self.trees.append({
    #             'state': node.state,
    #             'name': node.__repr_name__(),
    #             'children': []
    #         })
    #         return
    #
    #     def iter_tree(tree: list, search_for: str):
    #         for item in tree:
    #             if item['state'] == search_for:
    #                 return item
    #             else:
    #                 result = iter_tree(item['children'], search_for)
    #                 if result:
    #                     return result
    #     parent = iter_tree(self.trees, ancestor.state)
    #     parent['children'].append({
    #             'state': node.state,
    #             'name': node.__repr_name__(),
    #             'children': []
    #         })
    #     print(ujson.dumps(self.trees))

