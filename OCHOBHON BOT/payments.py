from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from config import PROVIDER_TOKEN, ADMIN_ID
from database import (
    get_service, create_payment, get_payment_by_payload,
    set_payment_status
)

router = Router()


@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_stars(call: CallbackQuery):
    sid = int(call.data.split(":")[1])
    s = get_service(sid)
    if not s:
        await call.answer("Услуга не найдена", show_alert=True)
        return
    _, title, desc, price, stars, rub = s
    if not stars:
        await call.answer("Цена в звёздах не задана", show_alert=True)
        return

    payload = f"stars:{call.from_user.id}:{sid}"
    create_payment(call.from_user.id, None, sid, stars, "XTR", "stars", payload)

    await call.message.answer_invoice(
        title=title,
        description=desc[:255],
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=stars)],
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay_fiat:"))
async def pay_fiat(call: CallbackQuery):
    sid = int(call.data.split(":")[1])
    s = get_service(sid)
    if not s:
        await call.answer("Услуга не найдена", show_alert=True)
        return
    _, title, desc, price, stars, rub = s
    if not rub:
        await call.answer("Цена в рублях не задана", show_alert=True)
        return
    if not PROVIDER_TOKEN:
        await call.answer("Оплата картой пока не подключена", show_alert=True)
        return

    payload = f"fiat:{call.from_user.id}:{sid}"
    create_payment(call.from_user.id, None, sid, rub, "RUB", "fiat", payload)

    await call.message.answer_invoice(
        title=title,
        description=desc[:255],
        payload=payload,
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=title, amount=rub * 100)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def paid(message: Message):
    payload = message.successful_payment.invoice_payload
    row = get_payment_by_payload(payload)
    if row:
        set_payment_status(row[0], "paid")

    amount = message.successful_payment.total_amount
    currency = message.successful_payment.currency

    await message.answer(
        f"Оплата получена.\n\n"
        f"Сумма: {amount / 100 if currency == 'RUB' else amount} {currency}\n\n"
        f"Я свяжусь с вами для уточнения деталей.",
    )

    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"💰 Новая оплата\n\n"
            f"Пользователь: @{message.from_user.username or message.from_user.id}\n"
            f"Сумма: {amount / 100 if currency == 'RUB' else amount} {currency}\n"
            f"Payload: {payload}"
        )
    except Exception:
        pass
