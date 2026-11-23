import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import (
    BOT_TOKEN,
    LAMINATION_COEF,
    MANAGER_CHAT_ID,
    MOSQUITO_NET_PRICE,
    OPENING_TYPES,
    PROFILES,
    TURNKEY_BASE_PRICE,
    TURNKEY_PER_M2,
    WEBAPP_HOST,
    WEBAPP_PORT,
    WINDOW_TYPES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TOKEN = (os.getenv("BOT_TOKEN") or BOT_TOKEN).strip()
bot = Bot(token=TOKEN)
dp = Dispatcher()


class CalcStates(StatesGroup):
    choosing_type = State()
    choosing_profile = State()
    entering_window_size = State()
    entering_door_size = State()
    choosing_opening = State()
    choosing_package = State()
    choosing_extras = State()
    waiting_phone = State()


def get_types_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=v["name"], callback_data=f"type:{k}")]
        for k, v in WINDOW_TYPES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profiles_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{v['name']} — от {v['price_m2']} грн/м²",
                callback_data=f"prof:{k}",
            )
        ]
        for k, v in PROFILES.items()
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:type")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_opening_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{v['name']}" + (f" (+{v['extra_price']} грн)" if v["extra_price"] else ""),
                callback_data=f"open:{k}",
            )
        ]
        for k, v in OPENING_TYPES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_package_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛠 Под ключ (монтаж, подоконник, отлив, доставка)", callback_data="pkg:turnkey")],
            [InlineKeyboardButton(text="🪟 Только изделие (без монтажа)", callback_data="pkg:window_only")],
        ]
    )


def get_extras_kb(lamination: bool, net: bool) -> InlineKeyboardMarkup:
    lam_mark = "✅" if lamination else "⬜"
    net_mark = "✅" if net else "⬜"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{lam_mark} Ламинация профиля (+25%)", callback_data="extra:lam")],
            [InlineKeyboardButton(text=f"{net_mark} Москитная сетка (+{MOSQUITO_NET_PRICE} грн)", callback_data="extra:net")],
            [InlineKeyboardButton(text="🧮 Рассчитать стоимость", callback_data="extra:done")],
        ]
    )


def get_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Заказать бесплатный замер и точный расчет", callback_data="order:lead")],
            [InlineKeyboardButton(text="🔄 Посчитать другое окно", callback_data="order:restart")],
        ]
    )


def parse_dimensions(text: str) -> tuple[int, int] | None:
    nums = re.findall(r"\d+", text)
    if len(nums) != 2:
        return None
    w, h = int(nums[0]), int(nums[1])
    if 30 <= w <= 450 and 30 <= h <= 450:
        w *= 10
        h *= 10
    if not (300 <= w <= 5000 and 300 <= h <= 3500):
        return None
    return w, h


def calculate_price(data: dict) -> dict:
    w_type = WINDOW_TYPES[data["window_type"]]
    profile = PROFILES[data["profile"]]
    opening = OPENING_TYPES[data["opening"]]

    win_w, win_h = data["win_size"]
    area_m2 = (win_w * win_h) / 1_000_000

    if w_type["is_balcony"] and "door_size" in data:
        door_w, door_h = data["door_size"]
        area_m2 += (door_w * door_h) / 1_000_000

    base_product = area_m2 * profile["price_m2"] * w_type["area_coef"]
    if data.get("lamination"):
        base_product *= LAMINATION_COEF

    total = base_product + opening["extra_price"]

    if data.get("mosquito_net"):
        total += MOSQUITO_NET_PRICE

    if data["package"] == "turnkey":
        total += TURNKEY_BASE_PRICE + (area_m2 * TURNKEY_PER_M2)

    return {
        "area_m2": round(area_m2, 2),
        "total": int(round(total, -1)),
    }


@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    logging.info(f"Получен /start от user_id={message.from_user.id}")
    await state.clear()
    await state.set_state(CalcStates.choosing_type)
    await message.answer(
        "👋 Добро пожаловать в калькулятор окон **Ekipazh**!\n\n"
        "Выберите тип конструкции, который хотите рассчитать:",
        reply_markup=get_types_kb(),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data == "order:restart")
async def restart_calc(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(CalcStates.choosing_type)
    await callback.message.edit_text(
        "Выберите тип конструкции:",
        reply_markup=get_types_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "back:type")
async def back_to_type(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcStates.choosing_type)
    await callback.message.edit_text(
        "Выберите тип конструкции:",
        reply_markup=get_types_kb(),
    )
    await callback.answer()


@dp.callback_query(CalcStates.choosing_type, F.data.startswith("type:"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    type_key = callback.data.split(":")[1]
    await state.update_data(window_type=type_key)
    await state.set_state(CalcStates.choosing_profile)
    await callback.message.edit_text(
        f"Выбрано: **{WINDOW_TYPES[type_key]['name']}**\n\n"
        "Теперь выберите профильную систему:",
        reply_markup=get_profiles_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.callback_query(CalcStates.choosing_profile, F.data.startswith("prof:"))
async def process_profile(callback: types.CallbackQuery, state: FSMContext):
    prof_key = callback.data.split(":")[1]
    await state.update_data(profile=prof_key)
    data = await state.get_data()
    is_balcony = WINDOW_TYPES[data["window_type"]]["is_balcony"]

    await state.set_state(CalcStates.entering_window_size)
    prompt = (
        "Введите размеры **окна** (ширина × высота в мм), например: `800x1400`"
        if is_balcony
        else "Введите размеры окна (ширина × высота в мм), например: `1300x1400`"
    )
    await callback.message.edit_text(prompt, parse_mode="Markdown")
    await callback.answer()


@dp.message(CalcStates.entering_window_size)
async def process_window_size(message: types.Message, state: FSMContext):
    dims = parse_dimensions(message.text or "")
    if not dims:
        await message.answer(
            "❌ Не удалось распознать размеры. Введите ширину и высоту в миллиметрах, например: `1200x1400`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(win_size=dims)
    data = await state.get_data()

    if WINDOW_TYPES[data["window_type"]]["is_balcony"]:
        await state.set_state(CalcStates.entering_door_size)
        await message.answer(
            "Теперь введите размеры **балконной двери** (ширина × высота в мм), например: `700x2100`",
            parse_mode="Markdown",
        )
    else:
        await state.set_state(CalcStates.choosing_opening)
        await message.answer(
            f"Размеры приняты: **{dims[0]} × {dims[1]} мм**.\n"
            "Выберите вариант открывания створок:",
            reply_markup=get_opening_kb(),
            parse_mode="Markdown",
        )


@dp.message(CalcStates.entering_door_size)
async def process_door_size(message: types.Message, state: FSMContext):
    dims = parse_dimensions(message.text or "")
    if not dims:
        await message.answer(
            "❌ Неверный формат. Введите ширину и высоту двери в мм, например: `700x2100`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(door_size=dims)
    await state.set_state(CalcStates.choosing_opening)
    await message.answer(
        f"Размеры двери приняты: **{dims[0]} × {dims[1]} мм**.\n"
        "Выберите вариант открывания створок:",
        reply_markup=get_opening_kb(),
        parse_mode="Markdown",
    )


@dp.callback_query(CalcStates.choosing_opening, F.data.startswith("open:"))
async def process_opening(callback: types.CallbackQuery, state: FSMContext):
    open_key = callback.data.split(":")[1]
    await state.update_data(opening=open_key)
    await state.set_state(CalcStates.choosing_package)
    await callback.message.edit_text(
        "Выберите вариант комплектации:",
        reply_markup=get_package_kb(),
    )
    await callback.answer()


@dp.callback_query(CalcStates.choosing_package, F.data.startswith("pkg:"))
async def process_package(callback: types.CallbackQuery, state: FSMContext):
    pkg_key = callback.data.split(":")[1]
    await state.update_data(package=pkg_key, lamination=False, mosquito_net=False)
    await state.set_state(CalcStates.choosing_extras)
    await callback.message.edit_text(
        "Отметьте дополнительные опции (при необходимости) и нажмите **«Рассчитать стоимость»**:",
        reply_markup=get_extras_kb(False, False),
        parse_mode="Markdown",
    )
    await callback.answer()


@dp.callback_query(CalcStates.choosing_extras, F.data.startswith("extra:"))
async def process_extras(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    data = await state.get_data()

    if action == "lam":
        new_val = not data.get("lamination", False)
        await state.update_data(lamination=new_val)
        await callback.message.edit_reply_markup(
            reply_markup=get_extras_kb(new_val, data.get("mosquito_net", False))
        )
        await callback.answer()
    elif action == "net":
        new_val = not data.get("mosquito_net", False)
        await state.update_data(mosquito_net=new_val)
        await callback.message.edit_reply_markup(
            reply_markup=get_extras_kb(data.get("lamination", False), new_val)
        )
        await callback.answer()
    elif action == "done":
        calc = calculate_price(data)
        await state.update_data(calculated_total=calc["total"], area_m2=calc["area_m2"])

        w_type = WINDOW_TYPES[data["window_type"]]["name"]
        prof = PROFILES[data["profile"]]["name"]
        opening = OPENING_TYPES[data["opening"]]["name"]
        win_w, win_h = data["win_size"]

        size_str = f"{win_w} × {win_h} мм"
        if "door_size" in data:
            dw, dh = data["door_size"]
            size_str += f" + дверь {dw} × {dh} мм"

        pkg_str = (
            "Под ключ (подоконник 250 мм, отлив 150 мм, монтаж, доставка)"
            if data["package"] == "turnkey"
            else "Только изделие"
        )
        extras_list = []
        if data.get("lamination"):
            extras_list.append("Ламинация")
        if data.get("mosquito_net"):
            extras_list.append("Москитная сетка")
        extras_str = ", ".join(extras_list) if extras_list else "Нет"

        summary = (
            f"📋 **Предварительный расчет Ekipazh**\n\n"
            f"• **Конструкция:** {w_type}\n"
            f"• **Профиль:** {prof}\n"
            f"• **Размеры:** {size_str} ({calc['area_m2']} м²)\n"
            f"• **Открывание:** {opening}\n"
            f"• **Комплектация:** {pkg_str}\n"
            f"• **Доп. опции:** {extras_str}\n\n"
            f"💰 **Ориентировочная стоимость: ~{calc['total']:,} грн**\n\n"
            f"_Точную стоимость подтвердит инженер после бесплатного замера._"
        ).replace(",", " ")

        await state.update_data(summary_text=summary)
        await callback.message.edit_text(summary, reply_markup=get_result_kb(), parse_mode="Markdown")
        await callback.answer()


@dp.callback_query(F.data == "order:lead")
async def request_contact(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(CalcStates.waiting_phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить мой номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await callback.message.answer(
        "Оставьте ваш номер телефона (кнопкой ниже или напишите вручную), и инженер свяжется с вами для согласования замера:",
        reply_markup=kb,
    )
    await callback.answer()


@dp.message(CalcStates.waiting_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if len(phone) < 7:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return

    data = await state.get_data()
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"

    lead_text = (
        f"🔥 **Новая заявка из бота-калькулятора!**\n\n"
        f"👤 **Клиент:** {user.full_name} ({username})\n"
        f"📞 **Телефон:** `{phone}`\n\n"
        f"{data.get('summary_text', '')}"
    )

    env_mgr = (os.getenv("MANAGER_CHAT_ID") or "").strip()
    mgr_id = int(env_mgr) if env_mgr.isdigit() else MANAGER_CHAT_ID
    target_chat = mgr_id if mgr_id else user.id
    try:
        await bot.send_message(target_chat, lead_text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки заявки менеджеру: {e}")

    await message.answer(
        "✅ **Заявка принята!**\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    await state.clear()


async def on_startup(bot: Bot) -> None:
    bot_id = int(TOKEN.split(":")[0])
    bot._me = User(id=bot_id, is_bot=True, first_name="EkipazhBot")
    logging.info("Сервер запущен БЕЗ вызова setWebhook (используется вебхук, привязанный в Telegram).")


async def on_shutdown(bot: Bot) -> None:
    await bot.session.close()


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="Ekipazh Bot is running!")


def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    app.router.add_get("/", healthcheck)

    webhook_path = f"/webhook/{TOKEN}"
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=webhook_path)
    setup_application(app, dp, bot=bot)

    port = int(os.getenv("PORT", WEBAPP_PORT))
    logging.info(f"Запуск веб-сервера на порту {port}...")
    web.run_app(app, host=WEBAPP_HOST, port=port)


if __name__ == "__main__":
    main()
