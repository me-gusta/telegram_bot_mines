import base64
import datetime
import logging
from contextlib import suppress
from functools import cached_property
from typing import List, Any, Union, Callable

import ujson
from aiogram import types, Bot
from aiogram.utils.exceptions import MessageToEditNotFound, MessageNotModified
from pydantic import BaseModel

from core.logging_config import root_logger
from db.engine import session
from db.helpers import get_or_create_user
from db.models import User
from handlers_bot.common import answer_query
from handlers_bot.telegram_dispatcher import TelegramDispatcher
from i18n import _


def is_msg(update: Any):
    return isinstance(update, types.Message)


def is_cq(update: Any):
    return isinstance(update, types.CallbackQuery)


class RenderProps(BaseModel):
    should_render: bool = True
    new_message: bool = False
    redirect_to: Union['Node', None] = None


class Node(BaseModel):
    emoji: str = ''
    print_footer = True
    print_header = True

    commands = []  # List[str] - add node as a command

    ancestor: Union['Node', None] = None
    children = []  # List[List[Node]] - children nodes on a button grid

    on_text: bool = False  # should listen every Message update call

    back_btn: bool = False  # show back btn
    menu_btn: bool = False  # show menu btn

    logger: logging.Logger = None

    pass_data: Any = None  # data that should be passed to the next node on btn click

    # variable_state: str = ''  # for nodes which must be unique

    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)

    def __repr__(self):
        return f'<Node: {self.__repr_name__()}>'

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.logger = root_logger.getChild('node').getChild(self.__repr_name__())

    @property
    def title(self) -> str:
        return 'Node'

    @property
    def header(self) -> str:
        return self._full_title

    @property
    def footer(self) -> str:
        return _('Choose an Option')

    @property
    def message(self) -> str:
        """
        Customize this method to edit rendered message
        :return:
        """
        return ''

    async def render(self, update: Union[types.CallbackQuery, types.Message]) -> RenderProps:
        """
        Override this method to edit logic that has to be run on node processing.
        You would want to use is_msg and is_cq to determine the type of an update
        :return: Should dispatching be continued?
        """
        return RenderProps()

    async def pre_render(self):
        """
        Override this method to edit some properties before render. For instance, set default values
        :return:
        """
        self.logger.debug('PRE_RENDER')

    def buttons(self) -> List[List[types.InlineKeyboardButton]]:
        return [[node.as_button(from_state=self.state) for node in group] for group in self.children]

    @cached_property
    def state(self) -> str:
        return f'{self.__repr_name__()}'  # + self.variable_state

    @property
    def user(self) -> User:
        """
        Shorthand for getting user from DB
        :return:
        """
        return TelegramDispatcher.get_current_user()

    def _compile_text(self):
        """
        :return: Compiled text to be rendered to user
        """
        text = f'*{self.header}*\n\n' if self.print_header else ''
        text += f'{self.message}'
        text += f'\n\n*{self.footer}*' if self.print_footer else ''
        return text

    @property
    def _full_title(self) -> str:
        return self.emoji + ' ' + self.title

    @property
    def _buttons(self) -> List[List[types.InlineKeyboardButton]]:
        """
        Transform child nodes into buttons
        :return:
        """
        self.logger.debug('_buttons')
        buttons = self.buttons()

        if self.ancestor and self.back_btn:
            buttons.append([
                Reference(emoji='<', custom_title=_('Back'), to_node=self.ancestor.state).as_button(
                    from_state=self.state)
            ])
        if self.menu_btn:
            buttons.append([
                Reference(custom_title=_('Menu'), to_node='MainMenu').as_button(from_state=self.state)
            ])
        return buttons

    def as_button(self, from_state, data: Union[dict, None] = None) -> types.InlineKeyboardButton:
        """
        :param from_state: node transitioned from
        :param data: additional data
        :return: InlineKeyboardButton of the node
        """
        # t and f = to_state and from_state. Use short names to fit 64-byte limit
        if data is None:
            data = {}
        data_dict = {'t': self.state,
                     'f': from_state}
        data_dict.update(data)
        callback_data = base64.b64encode(
            ujson.dumps(data_dict).encode('utf-8')
        ).decode('utf-8')
        return types.InlineKeyboardButton(
            text=self._full_title,
            callback_data=callback_data)

    async def _set_user_state(self, update: Union[types.CallbackQuery, types.Message]):
        self.user.state = self.state
        children = [x for group in self.children for x in group]
        print(children)
        if is_cq(update):
            self.user.menu_message_id = update.message.message_id

    async def _commit_database(self):
        session.commit()

    @property
    def _dispatch(self):
        """
        :return: dispatch method that handles CallbackQuery updates
        """

        async def dispatch(update: Union[types.CallbackQuery, types.Message]):
            await self._set_user_state(update)
            await self.pre_render()
            self.logger.debug('RENDER START')

            render_props = await self.render(update)
            self.logger.debug('RENDER OVER; props: %s', render_props)

            await self._commit_database()
            if not render_props.should_render:
                return

            if render_props.redirect_to:
                await render_props.redirect_to._dispatch(update)
                return
            elif render_props.new_message:
                await Bot.get_current().send_message(
                    chat_id=self.user.user_id,
                    text=self._compile_text(),
                    reply_markup=types.InlineKeyboardMarkup(1, self._buttons),
                    parse_mode='markdown')
                return

            if is_cq(update):
                await answer_query(update, self._compile_text(), self._buttons)
            elif is_msg(update):
                with suppress(MessageNotModified):
                    await Bot.get_current().edit_message_text(
                        chat_id=self.user.user_id,
                        message_id=self.user.menu_message_id,
                        text=self._compile_text(),
                        reply_markup=types.InlineKeyboardMarkup(1, self._buttons),
                        parse_mode='markdown')

        return dispatch

    def setup(self, dp: TelegramDispatcher, ancestor=None):
        def filter_callback_query(query: types.CallbackQuery):
            """
            Filters if this node should dispatch the query
            :param query:
            :return:
            """
            data = ujson.loads(base64.b64decode(query.data))
            return data.get('t') == self.state

        def filter_on_text(_: types.Message):
            """
            Filters if this node should dispatch the message.
            :param _:
            :return:
            """
            return TelegramDispatcher.get_current_user().state == self.state

        if self.__repr_name__() not in dp.connected_nodes:
            dp.connected_nodes.append(self.__repr_name__())
            self.logger.info('setup. connect callback query handler')
            dp.register_callback_query_handler(self._dispatch, filter_callback_query)

            if self.commands:
                self.logger.info(f'setup. connect commands: {self.commands}')
                dp.register_message_handler(self._dispatch, commands=self.commands)

            if self.on_text:
                self.logger.info(f'setup. connect on_text')
                dp.register_message_handler(self._dispatch, filter_on_text)

        for group in self.children:
            for node in group:
                node.setup(dp, self)

        self.ancestor = ancestor


class Reference(Node):
    to_node: str = None
    custom_title: str = None

    @property
    def title(self) -> str:
        return self.custom_title

    @cached_property
    def state(self) -> str:
        return self.to_node


class Link(Node):
    custom_title: Callable[[], str]
    url = 'https://example.com'

    @property
    def title(self) -> str:
        return self.custom_title()

    def as_button(self, from_state, data: Union[dict, None] = None) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(
            text=self._full_title,
            url=self.url)
