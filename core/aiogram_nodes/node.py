import functools
from typing import Union, Any, Type, List, Optional

from aiogram import types, Bot
from aiogram.utils.exceptions import MessageNotModified
from pydantic import BaseModel

from core.config_loader import config
from core.constants import URL_SUPPORT
from core.logging_config import root_logger
from core.aiogram_nodes.telegram_dispatcher import TelegramDispatcher
from core.aiogram_nodes.util import encode_callback_data, decode_callback_data, is_msg, is_cq, \
    get_current_user
from core.aiogram_nodes.state_management import StateManager
from db.engine import dbs
from i18n import _


class Shortcuts:
    BUTTON_TYPE = 't'
    TRANSITION_TO_NODE = 'n'
    TRANSITION_TO_NODE_PROPS = 'x'


class Button:
    text: str = ''
    data: dict

    def _compile_text(self) -> str:
        return self.text

    def compile(self) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(text=self._compile_text(),
                                          callback_data=encode_callback_data(self.data))


class TransitionButton(Button):
    to_node: Union['Node', None]

    def __init__(self, to_node: Union[Type['Node'], str], props: dict = None, text: str = ''):
        self.text = text
        data = {}
        if not props:
            props = {}

        if isinstance(to_node, str):
            if to_node.isdigit():
                data[Shortcuts.TRANSITION_TO_NODE] = to_node
            else:
                data[Shortcuts.TRANSITION_TO_NODE] = StateManager.get(to_node)
            self.to_node = None
        else:
            self.to_node = to_node(**props)
            data[Shortcuts.TRANSITION_TO_NODE] = to_node.state()
        data[Shortcuts.TRANSITION_TO_NODE_PROPS] = props
        self.data = data

    def _compile_text(self) -> str:
        text = super(TransitionButton, self)._compile_text()
        if not text:
            if self.to_node:
                text = self.to_node.emoji + ' ' + self.to_node.title
            else:
                text = '--'
        return text


class BackButton(TransitionButton):
    def __init__(self, **kwargs):
        super().__init__(text='<' + ' ' + _('Back'), **kwargs)


class URLButton(Button):
    url: str = ''
    is_webapp: bool

    def __init__(self, text: str, url: str, is_webapp=False):
        self.text = text
        self.url = url
        self.data = {}
        self.is_webapp = is_webapp

    def compile(self) -> types.InlineKeyboardButton:
        if self.is_webapp:
            return types.InlineKeyboardButton(text=self._compile_text(), web_app=types.WebAppInfo(url=self.url))
        else:
            return types.InlineKeyboardButton(text=self._compile_text(), url=self.url)


class SkipMessageEditing(Exception):
    pass


class Node:
    emoji = ''

    show_header = True
    show_footer = True

    props: Any = None

    commands = []
    on_text = False

    back_to: str = None
    menu_btn: bool = False

    only_admin: bool = False

    parse_mode: Optional[str] = 'markdown'

    class Props(BaseModel):
        any: Any

    def __init__(self, back_to=None, **kwargs):
        if back_to:
            self.back_to = back_to
        self._logger = root_logger.getChild('Node.' + self.__repr_name__() + ' ' + self.state())
        self.props = self.Props(**kwargs)

    def __repr_name__(self):
        return self.__class__.__name__

    _state = ''
    _logger = None

    @classmethod
    @functools.lru_cache()
    def state(cls):
        if cls._state and cls.__base__._state != cls._state:
            return cls._state
        state = StateManager.generate_simple(cls)
        cls._state = state
        return cls._state

    @property
    def title(self) -> str:
        return 'Nothing'

    @property
    def header(self) -> str:
        return self.emoji + ' ' + self.title

    @property
    def footer(self) -> str:
        return _('Choose an Option')

    async def text(self) -> str:
        return ''

    @property
    def buttons(self) -> List[List[Button]]:
        return []

    async def process(self, update: Union[types.CallbackQuery, types.Message]) -> Union['Node', None]:
        pass

    def _compile_markup(self) -> types.InlineKeyboardMarkup:
        buttons = self.buttons
        if self.back_to:
            buttons += [
                [BackButton(to_node=self.back_to)]
            ]
        if self.menu_btn:
            buttons += [
                [TransitionButton(to_node='MainMenu', text='🏠' + ' ' + _('Main Menu'))]
            ]
        return types.InlineKeyboardMarkup(inline_keyboard=[
            [x.compile() for x in group] for group in buttons])

    @property
    def dispatch(self):
        async def _dispatch(update: Union[types.CallbackQuery, types.Message]):
            self._logger.info('start dispatch')
            # before
            if is_cq(update):
                decoded_data = decode_callback_data(update.data)
                if decoded_data[Shortcuts.TRANSITION_TO_NODE] == self.state() and decoded_data.get(
                        Shortcuts.TRANSITION_TO_NODE_PROPS):
                    self.props = self.Props(**decoded_data.get(Shortcuts.TRANSITION_TO_NODE_PROPS))
            self._logger.info('props: %s', self.props)

            user = get_current_user()
            user.state = self.state()
            if is_cq(update):
                user.menu_message_id = update.message.message_id

            # process
            self._logger.info('process()')
            if self.only_admin and update.from_user.id != config.operator_id:
                self._logger.info('skip process. user is not an operator')
                switch_node = NullNode()
            else:
                switch_node = await self.process(update)

            dbs.users.update_one({'_id': user.id}, {'$set': user.dict()})

            # switch
            if switch_node:
                self._logger.info('switching node to %s', switch_node)
                # reset
                self.props = self.Props()
                if isinstance(switch_node, NullNode):
                    return
                await switch_node.dispatch(update)
                return

            # compile
            text = await self._compile_text()
            markup = self._compile_markup()
            # reset
            self.props = self.Props()

            # send
            try:
                if is_msg(update) and update.is_command():
                    raise SkipMessageEditing
                await Bot.get_current().edit_message_text(
                    chat_id=user.user_id,
                    message_id=user.menu_message_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode=self.parse_mode)
            except (MessageNotModified, SkipMessageEditing):
                await Bot.get_current().send_message(
                    chat_id=user.user_id,
                    text=text,
                    reply_markup=markup,
                    parse_mode=self.parse_mode)

            if is_cq(update):
                await update.answer()

        return _dispatch

    async def _compile_text(self):
        """
        :return: Compiled text to be rendered to user
        """
        text = f'*{self.header}*\n\n' if self.show_header else ''
        text += f'{await self.text()}'
        text += f'\n\n*{self.footer}*' if self.show_footer else ''
        return text

    def setup(self, dp: TelegramDispatcher):
        async def filter_callback_query(call: types.CallbackQuery):

            data = decode_callback_data(call.data)
            return self.state() == data.get(Shortcuts.TRANSITION_TO_NODE)

        async def filter_on_text(message: types.Message):
            return get_current_user().state == self.state() and not message.is_command()

        if not dp.is_connected(self):
            dp.connect(self)
            self._logger.info('     setup. connect callback query handler')
            dp.register_callback_query_handler(self.dispatch, filter_callback_query)

            if self.commands:
                self._logger.info(f'     setup. connect commands: {self.commands}')
                dp.register_message_handler(self.dispatch, commands=self.commands)
            if self.on_text:
                self._logger.info(f'     setup. connect on_text')
                dp.register_message_handler(self.dispatch, filter_on_text)


class NullNode(Node):
    pass


class ErrorNode(Node):
    emoji = '🚫'
    menu_btn = True

    class Props(BaseModel):
        msg: str = ''

    @property
    def title(self) -> str:
        return _('Something went wrong....')

    async def text(self) -> str:
        msg = self.props.msg + '\n\n' if self.props.msg else ''
        return msg + _('Please contact our support for details or try again.')

    @property
    def buttons(self) -> List[List[Button]]:
        return [
            [URLButton(url=URL_SUPPORT, text='🆘 ' + _('Support'))]
        ]