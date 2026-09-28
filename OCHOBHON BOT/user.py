import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, WebAppInfo
)
from config import ADMIN_ID, WEBAPP_URL
from database import (
    get_text, list_services, save_lead,
    get_user_leads, get_user_lead, get_service
)

router = Router()


class Form(StatesGroup):
    name = State()
    contact = State()
    service = State()
    task = State()


STATUS_ICONS = {"новая": "🆕", "в работе": "🔧", "готово": "✅", "отклонена": "❌"}


def main_menu():
    rows = [
        [KeyboardButton(text="Оставить заявку")],
        [KeyboardButton(text="Мои заявки")],
        [KeyboardButton(text="Услуги"), KeyboardButton(text="О нас")],
        [KeyboardButton(text="Контакты")],
    ]
    if WEBAPP_URL:
        rows.insert(1, [KeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url=WEBAPP_URL))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def services_kb():
    services = list_services()
    rows = [[KeyboardButton(text=s[1])] for s in services]
    rows.append([KeyboardButton(text="Отмена")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(get_text("welcome"), reply_markup=main_menu())


@router.message(F.text == "О нас")
async def about(message: Message):
    await message.answer(get_text("about"), reply_markup=main_menu())


@router.message(F.text == "Контакты")
async def contacts(message: Message):
    await message.answer(get_text("contacts"), reply_markup=main_menu())


@router.message(F.text == "Услуги")
async def services(message: Message):
    items = list_services()
    if not items:
        await message.answer("Услуги пока не добавлены.", reply_markup=main_menu())
        return
    kb_rows = []
    for s in items:
        sid, title, desc, price, stars, rub = s
        kb_rows.append([InlineKeyboardButton(
            text=f"{title} — {price}",
            callback_data=f"svc:{sid}"
        )])
    await message.answer(
        "Выберите услугу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )


@router.callback_query(F.data.startswith("svc:"))
async def service_view(call: CallbackQuery):
    sid = int(call.data.split(":")[1])
    s = get_service(sid)
    if not s:
        await call.answer("Не найдено", show_alert=True)
        return
    _, title, desc, price, stars, rub = s
    text = f"{title}\n\n{desc}\n\nЦена: {price}\n"
    if stars:
        text += f"Звёздами: {stars} ⭐\n"
    if rub:
        text += f"Картой: {rub} ₽\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Звёздами", callback_data=f"pay_stars:{sid}")],
        [InlineKeyboardButton(text="💳 Картой", callback_data=f"pay_fiat:{sid}")],
        [InlineKeyboardButton(text="Оставить заявку", callback_data=f"lead:{sid}")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("lead:"))
async def lead_from_service(call: CallbackQuery, state: FSMContext):
    sid = int(call.data.split(":")[1])
    s = get_service(sid)
    if not s:
        await call.answer("Не найдено", show_alert=True)
        return
    await state.update_data(service=s[1])
    await state.set_state(Form.name)
    await call.message.answer(get_text("ask_name"), reply_markup=ReplyKeyboardRemove())
    await call.answer()


@router.message(F.text == "Мои заявки")
async def my_leads(message: Message):
    leads = get_user_leads(message.from_user.id)
    if not leads:
        await message.answer("У вас пока нет заявок.", reply_markup=main_menu())
        return
    kb_rows = []
    for lid, service, status, created in leads:
        icon = STATUS_ICONS.get(status, "•")
        kb_rows.append([InlineKeyboardButton(
            text=f"{icon} №{lid} — {service} ({status})",
            callback_data=f"my:{lid}"
        )])
    await message.answer("Ваши заявки:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith("my:"))
async def my_lead_view(call: CallbackQuery):
    lead_id = int(call.data.split(":")[1])
    lead = get_user_lead(call.from_user.id, lead_id)
    if not lead:
        await call.answer("Заявка не найдена", show_alert=True)
        return
    lid, service, status, task, created, comment = lead
    icon = STATUS_ICONS.get(status, "•")
    text = (
        f"Заявка №{lid}\n\n"
        f"Услуга: {service}\n"
        f"Статус: {icon} {status}\n"
        f"Создана: {created}\n"
        f"Задача: {task}\n"
    )
    if comment:
        text += f"\nКомментарий:\n{comment}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обновить", callback_data=f"my:{lid}")],
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer("Обновлено")


@router.message(F.text == "Оставить заявку")
async def start_form(message: Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer(get_text("ask_name"), reply_markup=ReplyKeyboardRemove())


@router.message(Form.name)
async def f_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.contact)
    await message.answer(get_text("ask_contact"))


@router.message(Form.contact)
async def f_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    data = await state.get_data()
    if data.get("service"):
        await state.set_state(Form.task)
        await message.answer(get_text("ask_task"), reply_markup=ReplyKeyboardRemove())
    else:
        await state.set_state(Form.service)
        await message.answer(get_text("ask_service"), reply_markup=services_kb())


@router.message(Form.service)
async def f_service(message: Message, state: FSMContext):
    if message.text == "Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu())
        return
    await state.update_data(service=message.text)
    await state.set_state(Form.task)
    await message.answer(get_text("ask_task"), reply_markup=ReplyKeyboardRemove())


@router.message(Form.task)
async def f_task(message: Message, state: FSMContext):
    data = await state.get_data()
    lead_id = save_lead(
        message.from_user.id,
        message.from_user.username or "",
        data["name"], data["contact"], data["service"], message.text
    )
    await state.clear()
    await message.answer(
        get_text("after_lead").replace("{id}", str(lead_id)),
        reply_markup=main_menu()
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="В работу", callback_data=f"st:{lead_id}:в работе"),
            InlineKeyboardButton(text="Готово", callback_data=f"st:{lead_id}:готово"),
        ],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"st:{lead_id}:отклонена")],
    ])
    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"Новая заявка №{lead_id}\n\n"
            f"Имя: {data['name']}\n"
            f"Контакт: {data['contact']}\n"
            f"Услуга: {data['service']}\n"
            f"Задача: {message.text}\n"
            f"Username: @{message.from_user.username or 'нет'}",
            reply_markup=kb
        )
    except Exception as e:
        print("Не удалось уведомить админа:", e)


@router.message(F.web_app_data)
async def webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer("Ошибка данных.")
        return

    action = data.get("action")
    sid = data.get("service_id")

    if action == "pay_stars":
        await message.answer(
            "Создаю счёт в звёздах...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Оплатить", callback_data=f"pay_stars:{sid}")]
            ])
        )
    elif action == "pay_fiat":
        await message.answer(
            "Создаю счёт в рублях...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_fiat:{sid}")]
            ])
        )
