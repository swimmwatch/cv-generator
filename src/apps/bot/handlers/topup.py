import uuid

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import LabeledPrice
from aiogram.types import Message
from aiogram.types import PreCheckoutQuery
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import domains
from core import dto
from core import services
from infra.bot.template import TelegramTemplate
from utils.lang import _

from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)

_TOPUP_PREFIX = "topup_"
_TX_PAYLOAD_PREFIX = "tx_"


@router.message(Command("topup"))
@inject
async def topup(
    message: Message,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    lang = get_lang(message.from_user)
    text = telegram_template.render("balance/topup.html", lang)

    buttons = [
        [
            InlineKeyboardButton(
                text=f"{pack.credits} {_('credits')} — {pack.stars_price} ⭐",
                callback_data=f"{_TOPUP_PREFIX}{pack.name}",
            )
        ]
        for pack in domains.CreditPack
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_response(message, text, keyboard=markup)


@router.callback_query(F.data.startswith(_TOPUP_PREFIX))
@inject
async def topup_select(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    transaction_service: services.TransactionService = Provide["transaction_service"],
) -> None:
    pack_name = (callback.data or "")[len(_TOPUP_PREFIX) :]
    try:
        pack = domains.CreditPack[pack_name]
    except KeyError:
        await callback.answer(_("Invalid option."))
        return

    await callback.answer()

    if callback.from_user is None or callback.bot is None:
        return

    transaction = await transaction_service.create_pending(
        user_id=user.id,
        credits_amount=domains.CreditAmount(pack.credits),
        stars_amount=pack.stars_price,
    )

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"{pack.credits} {_('credits')}",
        description=_("Purchase %d credits for your account.") % pack.credits,
        payload=f"{_TX_PAYLOAD_PREFIX}{transaction.id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"{pack.credits} credits", amount=pack.stars_price)],
    )


@router.pre_checkout_query()
@inject
async def pre_checkout(
    query: PreCheckoutQuery,
    transaction_service: services.TransactionService = Provide["transaction_service"],
) -> None:
    payload = query.invoice_payload
    if not payload.startswith(_TX_PAYLOAD_PREFIX):
        await query.answer(ok=False, error_message=_("Invalid payment."))
        return

    tx_id_str = payload[len(_TX_PAYLOAD_PREFIX) :]
    try:
        tx_id = uuid.UUID(tx_id_str)
    except ValueError:
        await query.answer(ok=False, error_message=_("Invalid payment."))
        return

    await transaction_service.confirm(tx_id)
    await query.answer(ok=True)


@router.message(F.successful_payment)
@inject
async def successful_payment(
    message: Message,
    user: dto.UserOutDTO,
    transaction_service: services.TransactionService = Provide["transaction_service"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    payment = message.successful_payment
    if payment is None:
        return

    payload = payment.invoice_payload
    if not payload.startswith(_TX_PAYLOAD_PREFIX):
        return

    tx_id_str = payload[len(_TX_PAYLOAD_PREFIX) :]
    try:
        tx_id = uuid.UUID(tx_id_str)
    except ValueError:
        return

    telegram_payment_id = payment.telegram_payment_charge_id

    transaction = await transaction_service.complete(
        transaction_id=tx_id,
        telegram_payment_id=telegram_payment_id,
    )

    if not transaction:
        return

    lang = get_lang(message.from_user)
    text = telegram_template.render(
        "balance/topup_success.html",
        lang,
        credits=transaction.credits_amount,
        balance=user.balance + transaction.credits_amount,
    )
    await send_response(message, text)
