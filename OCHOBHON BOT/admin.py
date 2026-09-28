from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from config import ADMIN_ID
from database import (
    all_texts, set_text, get_text,
    list_services, add_service, update_service,
    toggle_service, delete_service,
    list_leads, get_lead, set_lead_status, count_leads,
    get_setting, set_setting,
    set_lead_comment, list_payments, count_payments_sum
)
from texts import TEXT_LABELS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class AdminForm(StatesGroup):
    edit_text_value = State()
    add_service_title = State()
    add_service_desc = State()
    add_service_price = State()
    add_service_stars = State()
    add_service_rub = State()
    edit_service_value = State()
    set_payment_amount = State()
    comment_text = State()


STATUS_MESSAGES = {
    "в работе": "Ваша заявка №{id} взята в работу. Я свяжусь с вами по указанному контакту.",
    "готово": "Заявка №{id} выполнена. Спасибо за обращение.",
    "отклонена": "Заявка №{id} отклонена. Если это ошибка — напишите мне напрямую.",
    "новая": "Статус заявки №{id} обновлён: новая.",
}


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Тексты бота", callback_data="adm:texts")],
        [InlineKeyboardButton(text="Услуги и цены", callback_data="adm:services")],
        [InlineKeyboardButton(text="Заявки", callback_data="adm:leads")],
        [InlineKeyboardButton(text="Платежи", callback_data="adm:payments")],
        [InlineKeyboardButton(text="Статистика", callback_data="adm:stats")],
    ])


@router.message(Command("admin"))
async def admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ-панель:", reply_markup=admin_kb())


@router.callback_query(F.data == "adm:texts")
async def texts_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    rows = []
    for key, _ in all_texts():
        label = TEXT_LABELS.get(key, key)
        rows.append([InlineKeyboardButton(text=label, callback_data=f"txt:{key}")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="adm:back")])
    await call.message.edit_text(
        "Выберите текст для редактирования:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


@router.callback_query(F.data.startswith("txt:"))
async def text_edit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split(":", 1)[1]
    current = get_text(key)
    await state.update_data(edit_text_key=key)
    await state.set_state(AdminForm.edit_text_value)
    await call.message.edit_text(
        f"Текущий текст ({key}):\n\n{current}\n\n"
        f"Отправьте новый текст одним сообщением."
    )
    await call.answer()


@router.message(AdminForm.edit_text_value)
async def text_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    set_text(data["edit_text_key"], message.text)
    await state.clear()
    await message.answer("Текст сохранён.", reply_markup=admin_kb())


@router.callback_query(F.data == "adm:services")
async def services_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    items = list_services(active_only=False)
    rows = []
    for s in items:
        sid, title, desc, price, stars, rub, active = s
        mark = "✅" if active else "❌"
        rows.append([InlineKeyboardButton(
            text=f"{mark} {title} — {price}",
            callback_data=f"srv:{sid}"
        )])
    rows.append([InlineKeyboardButton(text="+ Добавить услугу", callback_data="srv:add")])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="adm:back")])
    await call.message.edit_text("Услуги:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data == "srv:add")
async def srv_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminForm.add_service_title)
    await call.message.edit_text("Введите название услуги:")
    await call.answer()


@router.message(AdminForm.add_service_title)
async def srv_add_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text)
    await state.set_state(AdminForm.add_service_desc)
    await message.answer("Введите описание услуги:")


@router.message(AdminForm.add_service_desc)
async def srv_add_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(desc=message.text)
    await state.set_state(AdminForm.add_service_price)
    await message.answer("Введите цену текстом (например, от 150$):")


@router.message(AdminForm.add_service_price)
async def srv_add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(price=message.text)
    await state.set_state(AdminForm.add_service_stars)
    await message.answer("Введите цену в звёздах (целое число, 0 если не нужно):")


@router.message(AdminForm.add_service_stars)
async def srv_add_stars(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("Нужно целое число. Попробуйте снова:")
        return
    await state.update_data(stars=int(message.text))
    await state.set_state(AdminForm.add_service_rub)
    await message.answer("Введите цену в рублях (целое число, 0 если не нужно):")


@router.message(AdminForm.add_service_rub)
async def srv_add_rub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit():
        await message.answer("Нужно целое число. Попробуйте снова:")
        return
    data = await state.get_data()
    add_service(data["title"], data["desc"], data["price"], data["stars"], int(message.text))
    await state.clear()
    await message.answer("Услуга добавлена.", reply_markup=admin_kb())


@router.callback_query(F.data.startswith("srv:"))
async def srv_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    if parts[1] in ("add", "toggle", "del"):
        return
    sid = int(parts[1])
    items = [s for s in list_services(active_only=False) if s[0] == sid]
    if not items:
        await call.answer("Не найдено", show_alert=True)
        return
    s = items[0]
    _, title, desc, price, stars, rub, active = s
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data=f"srvf:{sid}:title")],
        [InlineKeyboardButton(text="Изменить описание", callback_data=f"srvf:{sid}:description")],
        [InlineKeyboardButton(text="Изменить цену текстом", callback_data=f"srvf:{sid}:price")],
        [InlineKeyboardButton(text="Изменить цену в звёздах", callback_data=f"srvf:{sid}:price_stars")],
        [InlineKeyboardButton(text="Изменить цену в рублях", callback_data=f"srvf:{sid}:price_rub")],
        [InlineKeyboardButton(text="Скрыть" if active else "Показать", callback_data=f"srv:toggle:{sid}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"srv:del:{sid}")],
        [InlineKeyboardButton(text="Назад", callback_data="adm:services")],
    ])
    await call.message.edit_text(
        f"{title}\n\n{desc}\n\nЦена: {price}\nЗвёзды: {stars}\nРубли: {rub}",
        reply_markup=kb
    )
    await call.answer()


@router.callback_query(F.data.startswith("srvf:"))
async def srv_edit_field(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    _, sid, field = call.data.split(":")
    await state.update_data(edit_sid=int(sid), edit_field=field)
    await state.set_state(AdminForm.edit_service_value)
    await call.message.edit_text(f"Отправьте новое значение для «{field}»:")
    await call.answer()


@router.message(AdminForm.edit_service_value)
async def srv_edit_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    field = data["edit_field"]
    value = message.text
    if field in ("price_stars", "price_rub"):
        if not value.isdigit():
            await message.answer("Нужно целое число.")
            return
        value = int(value)
    update_service(data["edit_sid"], field, value)
    await state.clear()
    await message.answer("Сохранено.", reply_markup=admin_kb())


@router.callback_query(F.data.startswith("srv:toggle:"))
async def srv_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    sid = int(call.data.split(":")[2])
    toggle_service(sid)
    await services_menu(call)


@router.callback_query(F.data.startswith("srv:del:"))
async def srv_del(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    sid = int(call.data.split(":")[2])
    delete_service(sid)
    await services_menu(call)


@router.callback_query(F.data == "adm:leads")
async def leads_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    rows = []
    for l in list_leads(20):
        lid, name, contact, service, status, created = l
        rows.append([InlineKeyboardButton(
            text=f"№{lid} | {name} | {status}",
            callback_data=f"lead:{lid}"
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="adm:back")])
    await call.message.edit_text(
        "Последние заявки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


@router.callback_query(F.data.startswith("lead:"))
async def lead_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    lid = int(call.data.split(":")[1])
    row = get_lead(lid)
    if not row:
        await call.answer("Нет заявки", show_alert=True)
        return

    _, user_id, username, name, contact, service, task, status, comment, created = row
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="В работу", callback_data=f"st:{lid}:в работе"),
            InlineKeyboardButton(text="Готово", callback_data=f"st:{lid}:готово"),
        ],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"st:{lid}:отклонена")],
        [InlineKeyboardButton(text="Комментарий", callback_data=f"cmt:{lid}")],
        [InlineKeyboardButton(text="Написать", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="adm:leads")],
    ])
    text = (
        f"Заявка №{lid}\n\n"
        f"Имя: {name}\n"
        f"Контакт: {contact}\n"
        f"Услуга: {service}\n"
        f"Задача: {task}\n"
        f"Статус: {status}\n"
        f"Создана: {created}\n"
    )
    if comment:
        text += f"Комментарий: {comment}\n"

    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("st:"))
async def set_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, lid, status = call.data.split(":", 2)
    lid_int = int(lid)

    set_lead_status(lid_int, status)
    await call.answer(f"Статус: {status}")

    row = get_lead(lid_int)
    if row:
        user_id = row[1]
        msg = STATUS_MESSAGES.get(status, f"Статус заявки №{lid_int}: {status}")
        try:
            await call.bot.send_message(
                user_id,
                msg.format(id=lid_int) + "\n\nПосмотреть: «Мои заявки»."
            )
        except Exception as e:
            print("Не удалось уведомить клиента:", e)


@router.callback_query(F.data.startswith("cmt:"))
async def cmt_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    lid = int(call.data.split(":")[1])
    await state.update_data(cmt_lead=lid)
    await state.set_state(AdminForm.comment_text)
    await call.message.edit_text(
        f"Введите комментарий к заявке №{lid}.\n"
        f"Клиент увидит его в карточке заявки."
    )
    await call.answer()


@router.message(AdminForm.comment_text)
async def cmt_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    lid = data["cmt_lead"]
    set_lead_comment(lid, message.text)
    await state.clear()

    row = get_lead(lid)
    if row:
        try:
            await message.bot.send_message(
                row[1],
                f"Комментарий к заявке №{lid}:\n\n{message.text}\n\n"
                f"Посмотреть: «Мои заявки»."
            )
        except Exception as e:
            print("Не удалось уведомить:", e)

    await message.answer("Комментарий сохранён.", reply_markup=admin_kb())


@router.callback_query(F.data == "adm:payments")
async def payments_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    rows = []
    for p in list_payments(20):
        pid, user_id, amount, currency, method, status, created = p
        rows.append([InlineKeyboardButton(
            text=f"№{pid} | {amount} {currency} | {method} | {status}",
            callback_data=f"pay_view:{pid}"
        )])
    rows.append([InlineKeyboardButton(text="Назад", callback_data="adm:back")])
    await call.message.edit_text(
        "Последние платежи:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


@router.callback_query(F.data.startswith("pay_view:"))
async def pay_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.answer("Детали платежа в разработке", show_alert=True)


@router.callback_query(F.data == "adm:stats")
async def stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    total_leads = count_leads()
    total_sum = count_payments_sum()
    await call.message.edit_text(
        f"Всего заявок: {total_leads}\n"
        f"Сумма оплат: {total_sum}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="adm:back")]
        ])
    )
    await call.answer()


@router.callback_query(F.data == "adm:back")
async def back(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("Админ-панель:", reply_markup=admin_kb())
    await call.answer()
