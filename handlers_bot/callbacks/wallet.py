import decimal
from decimal import Decimal

import aiohttp
import ujson
from aiogram import types, Dispatcher

from bot import bot
from core.config_loader import config
from core.constants import CRYPTO_PAY_URL, SUPPORT_USERNAME, MIN_DEPOSIT, MAX_DEPOSIT, \
    MIN_WITHDRAW, MAX_WITHDRAW
from core.logging_config import root_logger
from core.pure import to_decimal
from db.engine import session
from db.helpers import get_or_create_user
from db.models import Invoice, UserState, WithdrawRequest, User
from handlers_bot.common import answer_query, MenuCQ, WalletCQ, CryptoBotCQ, WithdrawRequestAcceptCQ
from i18n import _


async def wallet(query: types.CallbackQuery):
    """ Show wallet menu """
    user = await get_or_create_user(query.from_user, do_commit=False)
    user.state = UserState.NONE
    session.commit()
    text = _('👛 Wallet\n'
             '_Your Balance_: {balance} 💎\n\n'
             '*Choose an option*').format(balance=user.balance)

    buttons = [
        [types.InlineKeyboardButton('🔽 ' + _('Deposit'), callback_data=WalletCQ.DEPOSIT)],
        [types.InlineKeyboardButton('🔼 ' + _('Withdraw'), callback_data=WalletCQ.WITHDRAW)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=MenuCQ.MENU)]
    ]
    await answer_query(query, text, buttons)


async def deposit(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user, do_commit=False)
    user.state = UserState.NONE
    session.commit()

    text = _('🔼 Deposit\n'
             '⚠ Currently we are accepting Toncoin deposits only via @CryptoBot\n\n'
             '*Choose an option*')
    guide_url = _('https://telegra.ph/How-to-top-up-the-balance-of-the-LuckyTonBot-gaming-bot-using-CryptoBot-06-09')
    buttons = [
        [types.InlineKeyboardButton(_('🤖 @CryptoBot'), callback_data=CryptoBotCQ.PAYMENT_OPTION)],
        [types.InlineKeyboardButton(_('ℹ How to use @CryptoBot'), url=guide_url)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.WALLET)]
    ]
    await answer_query(query, text, buttons)


async def withdraw(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user, do_commit=False)
    user.state = UserState.on_withdraw_amount(query.message.message_id)
    session.commit()
    text = _('🔼 Withdraw\n'
             '_Your Balance_: {balance} 💎\n'
             '_Withdraw limit: from 0.5 up to 1000 💎_\n\n'
             '*Send amount you want to withdraw*').format(balance=user.balance)
    buttons = [
        [types.InlineKeyboardButton(_('About Withdrawals'), callback_data=WalletCQ.WITHDRAW_INFO)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.WALLET)]
    ]
    await answer_query(query, text, buttons)


async def withdraw_info(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user)
    text = _('⚠ Withdrawals can take up to 24h\n'
             '⚠ Minimum amount: 0.5 💎\n'
             '⚠ Maximum amount: 1000 💎').format(balance=user.balance)
    buttons = [
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.WITHDRAW)]
    ]
    await answer_query(query, text, buttons)


async def withdraw_request(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user, do_commit=False)
    user.state = UserState.NONE
    amount = WalletCQ.withdraw_request_get(query)
    request = WithdrawRequest(user=user, amount=amount)
    session.add(request)
    session.commit()
    operator_text = f'new withdrawal request\n' \
                    f'user: {user}\n' \
                    f'balance: {user.balance}\n' \
                    f'amount: {amount}\n\n' \
                    f'*choose option*'
    operator_buttons = [
        [types.InlineKeyboardButton('✅ ' + _('Confirm'), callback_data=WithdrawRequestAcceptCQ.accept(request.id))],
    ]
    await bot.send_message(chat_id=config.operator_id, text=operator_text, parse_mode='markdown',
                           reply_markup=types.InlineKeyboardMarkup(1, operator_buttons))

    text = _('Your withdrawal request is being proceeded\n'
             '⚠ Withdrawals can take up to 24h').format(balance=user.balance)
    buttons = [
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.WITHDRAW)]
    ]
    await answer_query(query, text, buttons)


async def cryptobot_payment_option(query: types.CallbackQuery):
    text = _('🤖 @Cryptobot deposit\n'
             '_Conversion rate: 1 TON = 1 💎_\n\n'
             '*Choose amount to deposit*')
    amounts = [[1, 10], [50, 100]]
    buttons = [[
        types.InlineKeyboardButton(f'{amount} TON', callback_data=CryptoBotCQ.confirm(amount)) for amount in group
    ] for group in amounts]
    buttons += [
        [types.InlineKeyboardButton(_('Custom Amount'), callback_data=CryptoBotCQ.CUSTOM_AMOUNT)],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.DEPOSIT)]
    ]
    await answer_query(query, text, buttons)


async def cryptobot_custom_amount(query: types.CallbackQuery):
    user = await get_or_create_user(query.from_user, do_commit=False)
    user.state = UserState.on_deposit_amount(query.message.message_id)
    session.commit()
    text = _('Send custom amount for deposit. From 0.5 to 1000 💎')

    buttons = [
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.DEPOSIT)]
    ]
    await answer_query(query, text, buttons)


async def cryptobot_confirm(query: types.CallbackQuery):
    root_logger.debug('cryptobot_confirm')
    amount: float = CryptoBotCQ.confirm_get(query)

    user = await get_or_create_user(query.from_user)
    root_logger.info(f'CONFIRM | {user=} {amount=}')

    text = _('Are you sure you want to deposit {} TON').format(amount)
    buttons = [
        [types.InlineKeyboardButton('✅ ' + _('Confirm'), callback_data=CryptoBotCQ.deposit(amount))],
        [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.DEPOSIT)]
    ]
    await answer_query(query, text, buttons)


async def cryptobot_deposit(query: types.CallbackQuery):
    root_logger.debug('cryptobot_deposit')
    amount: Decimal = CryptoBotCQ.deposit_get(query)
    headers = {
        'Crypto-Pay-API-Token': config.crypto_pay_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    async with aiohttp.ClientSession(headers=headers) as client_session:
        resp = await client_session.post(CRYPTO_PAY_URL + 'createInvoice',
                                         data={'asset': 'TON', 'amount': amount})
        text = await resp.text()
    root_logger.info(f'CRYPTO_PAY createInvoice {text=}')
    invoice_dict = ujson.loads(text)
    if not invoice_dict.get('ok'):
        text = _('Something went wrong. Please contact our support: @{}').format(SUPPORT_USERNAME)
        buttons = [[types.InlineKeyboardButton('⬅ ' + _('Menu'), callback_data=MenuCQ.MENU)]]
    else:
        user = await get_or_create_user(query.from_user, do_commit=False)
        invoice = Invoice(user=user, amount=amount, hash=invoice_dict['result']['hash'],
                          message_id=query.message.message_id)
        session.add(invoice)
        session.commit()
        text = _('To finish the payment:\n'
                 '1. Press "💳 Go to Payment"\n'
                 '2. Press "START"\n'
                 '3. Follow @CryptoBot instructions')
        buttons = [
            [types.InlineKeyboardButton('💳 ' + _('Go to Payment'),
                                        url='https://t.me/CryptoBot?start=' + invoice.hash)],
            [types.InlineKeyboardButton(_('Back to Menu'), callback_data=MenuCQ.MENU)],
        ]
    await answer_query(query, text, buttons)


async def on_text(message: types.Message):
    user = await get_or_create_user(message.from_user, do_commit=False)
    await message.delete()
    if user.state.startswith(UserState.ON_DEPOSIT_AMOUNT):
        try:
            amount = to_decimal(message.text.replace(',', '.'))
        except decimal.InvalidOperation:
            return
        if amount < MIN_DEPOSIT or amount > MAX_DEPOSIT:
            return
        query_message_id = int(user.state.split('-')[-1])
        text = _('Are you sure you want to deposit {} TON').format(amount)
        buttons = [
            [types.InlineKeyboardButton('✅ ' + _('Confirm'), callback_data=CryptoBotCQ.deposit(amount))],
            [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.DEPOSIT)]
        ]
        await bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=query_message_id,
            parse_mode='markdown',
            reply_markup=types.InlineKeyboardMarkup(1, buttons),
        )
    elif user.state.startswith(UserState.ON_WITHDRAW_AMOUNT):
        try:
            amount = to_decimal(message.text.replace(',', '.'))
        except decimal.InvalidOperation:
            return
        if amount > user.balance:
            return
        if amount < MIN_WITHDRAW or amount > MAX_WITHDRAW:
            return
        query_message_id = int(user.state.split('-')[-1])
        text = _('Are you sure you want to withdraw {} 💎').format(amount)
        buttons = [
            [types.InlineKeyboardButton('✅ ' + _('Confirm'), callback_data=WalletCQ.withdraw_request(amount))],
            [types.InlineKeyboardButton('⬅ ' + _('Back'), callback_data=WalletCQ.DEPOSIT)]
        ]
        await bot.edit_message_text(
            text=text,
            chat_id=message.chat.id,
            message_id=query_message_id,
            parse_mode='markdown',
            reply_markup=types.InlineKeyboardMarkup(1, buttons),
        )
    user.state = UserState.NONE
    session.commit()


async def withdrawal_request_accept(query: types.CallbackQuery):
    buttons = [
        [types.InlineKeyboardButton(text='OK', callback_data='close')]
    ]

    if query.from_user.id != config.operator_id:
        return
    request_id = WithdrawRequestAcceptCQ.accept_get(query)
    request: WithdrawRequest = session.query(WithdrawRequest).filter(WithdrawRequest.id == request_id).first()

    root_logger.info(f'withdrawal_request_accept. {request.user=}')
    if request.is_payed:
        text = f'withdrawal_request_accept. CANCELED. already payed'
        root_logger.info(text)
        await bot.send_message(config.operator_id, text=text)
        return
    if request.user.balance < request.amount:
        text = f'withdrawal_request_accept. CANCELED. not enough funds in user\'s wallet'
        root_logger.info(text)
        await bot.send_message(config.operator_id, text=text)
        await bot.send_message(request.user.user_id,
                               text=_('❌ Your withdrawal request has been declined.\n'
                                      'Reason: not enough funds in your wallet'),
                               reply_markup=types.InlineKeyboardMarkup(1, buttons))
        return

    headers = {
        'Crypto-Pay-API-Token': config.crypto_pay_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'asset': 'TON',
            'amount': request.amount,
            'user_id': request.user.user_id,
            'spend_id': str(hash(str(request.spend_id) + '.Iasgfuih'))}
    async with aiohttp.ClientSession(headers=headers) as client_session:
        resp = await client_session.post(CRYPTO_PAY_URL + 'transfer', data=data)
        response_data = ujson.loads(await resp.text())
    root_logger.info(f'withdrawal_request_accept. CRYPTO_PAY transfer {data=}\n {response_data=}')
    if not response_data['ok']:
        await bot.send_message(config.operator_id, text=f'ERROR\n{response_data=}')
    else:
        await bot.send_message(config.operator_id, text=f'SUCCESS\n{response_data=}')

    request.user.balance -= request.amount
    request.is_payed = True
    session.commit()

    text = _('✅ Your withdrawal request has been processed.\n'
             '{amount} 💎 sent to you wallet').format(amount=request.amount)

    await bot.send_message(request.user.user_id, text=text, reply_markup=types.InlineKeyboardMarkup(1, buttons))
    await query.answer()


def setup(dp: Dispatcher):
    dp.register_callback_query_handler(wallet, lambda call: call.data == WalletCQ.WALLET)

    dp.register_callback_query_handler(deposit, lambda call: call.data == WalletCQ.DEPOSIT)
    dp.register_callback_query_handler(withdraw, lambda call: call.data == WalletCQ.WITHDRAW)
    dp.register_callback_query_handler(withdraw_request, lambda call: call.data.startswith(WalletCQ.WITHDRAW_REQUEST))
    dp.register_callback_query_handler(withdraw_info, lambda call: call.data == WalletCQ.WITHDRAW_INFO)

    dp.register_message_handler(on_text)
    dp.register_callback_query_handler(cryptobot_payment_option, lambda call: call.data == CryptoBotCQ.PAYMENT_OPTION)
    dp.register_callback_query_handler(cryptobot_custom_amount, lambda call: call.data == CryptoBotCQ.CUSTOM_AMOUNT)
    dp.register_callback_query_handler(cryptobot_confirm, lambda call: call.data.startswith(CryptoBotCQ.CONFIRM))
    dp.register_callback_query_handler(cryptobot_deposit, lambda call: call.data.startswith(CryptoBotCQ.DEPOSIT))

    dp.register_callback_query_handler(withdrawal_request_accept,
                                       lambda call: call.data.startswith(WithdrawRequestAcceptCQ.ACCEPT))
