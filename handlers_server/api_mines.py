import hashlib
import random
import uuid
from decimal import Decimal, ROUND_DOWN

import ujson
from aiohttp import web
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_response import Response
from pydantic import BaseModel

from core import constants
from core.logging_config import root_logger
from core.mines_payouts import payouts_table
from db.engine import session
from db.helpers import get_running_mines_game
from db.models import MinesGame, MinesGameStatus
from handlers_server.helpers import validate_telegram_string, ApiView


async def index(request: web.Request):
    return Response(text='Hello! How is ur day today bro???')


class GetUserApi(ApiView):
    logger = root_logger.getChild('GetUserApi')

    class PostParams(BaseModel):
        data_check_string: str

    async def post(self):
        params = await self.retrieve_fetch_params(self.request)
        user = validate_telegram_string(params.data_check_string)
        last_game = get_running_mines_game(user)
        self.logger.info(f'User: {user}. Game: {last_game}')

        return self.json_response({'has_game': last_game is not None,
                                   'balance': user.balance,
                                   'language_code': user.language_code,
                                   'settings': user.mines_game_settings.dict()})


def generate_mine_field(mines_amount: int) -> dict:
    field_size = 25
    mines = random.sample(range(0, field_size), mines_amount)
    check_string = ''
    salt = random.randbytes(7).hex()
    for i in range(field_size):
        check_string += '*' if i in mines else '.'
    check_string += ';'
    check_string += salt
    hash_string = hashlib.md5(check_string.encode('utf-8')).hexdigest()
    return {'mines_json': ujson.dumps(mines), 'check_string': check_string, 'hash': hash_string}


class NewGameApi(ApiView):
    logger = root_logger.getChild('StartGameApi')

    class PostParams(BaseModel):
        data_check_string: str
        bet: float
        mines_amount: int

    async def post(self):
        params = await self.retrieve_fetch_params(self.request)
        user = validate_telegram_string(params.data_check_string, do_commit=False)
        last_game = get_running_mines_game(user)
        if last_game:
            return self.json_response(
                {'status': 'running', 'hash': last_game.hash, 'revealed': last_game.revealed})

        bet = Decimal(str(params.bet)).quantize(Decimal('.01'), ROUND_DOWN)

        if bet < constants.MIN_BET or bet > constants.MAX_BET:
            raise HTTPBadRequest(text='Bet is out of range')

        if bet > user.balance:
            raise HTTPBadRequest(text='Not enough funds in the wallet')

        if params.mines_amount > 24 or params.mines_amount < 1:
            raise HTTPBadRequest(text='Mines amount is out of range')

        game = MinesGame(
            user=user,
            bet=bet,
            **generate_mine_field(params.mines_amount)
        )
        session.add(game)
        user.mines_game_settings.last_bet = bet
        user.mines_game_settings.last_mines = params.mines_amount
        session.commit()
        self.logger.info(f'User: {user}; game: {game}')

        return self.json_response({'status': 'ok', 'hash': game.hash})


class RevealCellApi(ApiView):
    logger = root_logger.getChild('RevealCellApi')

    class PostParams(BaseModel):
        data_check_string: str
        cell_id: int

    async def post(self):
        params = await self.retrieve_fetch_params(self.request)
        user = validate_telegram_string(params.data_check_string, do_commit=False)
        last_game = get_running_mines_game(user)

        self.logger.info(f'cell: {params.cell_id}; game: {last_game}')

        if last_game is None or last_game.status != MinesGameStatus.RUNNING:
            raise HTTPBadRequest(text='No game running')
        if params.cell_id < 0 or params.cell_id > 25:
            raise HTTPBadRequest(text='Cell ID is out of range')
        if params.cell_id in last_game.revealed:
            raise HTTPBadRequest(text='Already revealed')

        # Lost game
        if params.cell_id in last_game.mines:
            self.logger.info('GAME LOST')
            user.change_balance(-last_game.bet)
            last_game.status = MinesGameStatus.LOST
            session.commit()
            return self.json_response({'status': 'lost',
                                       'check_string': last_game.check_string,
                                       'hash': last_game.hash,
                                       'mines': last_game.mines,
                                       'balance': user.balance})
        else:
            last_game.set_revealed(last_game.revealed + [params.cell_id])
            # Win game (revealed every cell)
            if len(last_game.revealed) + len(last_game.mines) == 25:
                last_game = MinesGameStatus.WON
                bet = Decimal(str(last_game.bet))
                win_amount = Decimal(
                    str(payouts_table[len(last_game.mines)][len(last_game.revealed) - 1])) * bet - bet
                user.change_balance(win_amount)
                session.commit()
                return self.json_response({
                    'status': 'won',
                    'check_string': last_game.check_string,
                    'hash': last_game.hash,
                    'mines': last_game.mines,
                    'balance': user.balance
                })

            # revealed one diamond
            session.commit()
            return self.json_response({
                'status': 'revealed',
            })


class CashoutApi(ApiView):
    logger = root_logger.getChild('RevealCellApi')

    class PostParams(BaseModel):
        data_check_string: str

    async def post(self):
        params = await self.retrieve_fetch_params(self.request)
        user = validate_telegram_string(params.data_check_string)
        last_game = get_running_mines_game(user)
        self.logger.info(f'user: {user}, game: {last_game}')

        if last_game is None or last_game.status != MinesGameStatus.RUNNING:
            raise HTTPBadRequest(text='No game running')
        if len(last_game.revealed) < 1:
            raise HTTPBadRequest(text='One must reveal at least 1 cell')

        bet = Decimal(str(last_game.bet))
        win_amount = (Decimal(str(payouts_table[len(last_game.mines)][len(last_game.revealed) - 1])) * bet) - bet
        last_game.status = MinesGameStatus.CASHOUT
        user.change_balance(win_amount)
        session.commit()
        return self.json_response({
            'status': 'won',
            'check_string': last_game.check_string,
            'hash': last_game.hash,
            'mines': last_game.mines,
            'balance': user.balance
        })
