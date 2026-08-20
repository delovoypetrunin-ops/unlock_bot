import asyncio
import logging
import sqlite3
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ContentType

# ========== ТОКЕН ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "2202 2080 1111 2308")
SUPPORT = "@PETRUNINNN"
# =================================================

PLANS = {
    "1": ("1 месяц", 429, "🎵"),
    "3": ("3 месяца", 1290, "🎶"),
    "6": ("6 месяцев", 2390, "🎧"),
    "12": ("12 месяцев", 4390, "🎸"),
}

DB = "unlock.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


def db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting_payment',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    return con


def add_order(user_id, username, plan, amount):
    con = db()
    cur = con.execute(
        "INSERT INTO orders(user_id, username, plan, amount) VALUES(?,?,?,?)",
        (user_id, username, plan, amount)
    )
    con.commit()
    order_id = cur.lastrowid
    con.close()
    return order_id


def get_order(order_id):
    con = db()
    row = con.execute(
        "SELECT id,user_id,username,plan,amount,status FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()
    con.close()
    return row


def set_status(order_id, status):
    con = db()
    con.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    con.commit()
    con.close()


def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Выбрать подписку", callback_data="plans")],
        [InlineKeyboardButton(text="❓ Поддержка", callback_data="support")]
    ])


def plans_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 1 месяц — 429 ₽", callback_data="plan:1")],
        [InlineKeyboardButton(text="🎶 3 месяца — 1290 ₽", callback_data="plan:3")],
        [InlineKeyboardButton(text="🎧 6 месяцев — 2390 ₽", callback_data="plan:6")],
        [InlineKeyboardButton(text="🎸 12 месяцев — 4390 ₽", callback_data="plan:12")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])


def payment_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="plans")]
    ])


def admin_payment_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{order_id}")
        ]
    ])


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🔓 UNLOCK\n"
        "официальные подписки Spotify\n\n"
        "🎵 ОТКРОЙ МИР МУЗЫКИ С ВЫГОДОЙ\n\n"
        "✅ Официальные подписки\n"
        "⚡ Быстрое подключение\n"
        "🔒 Безопасно и надёжно\n"
        "🆘 Поддержка 24/7",
        reply_markup=start_kb()
    )


@dp.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await call.message.answer(
        "❓ Поддержка\n\n"
        "По всем вопросам пишите:\n"
        f"{SUPPORT}\n\n"
        "⏰ Время ответа: 5 минут - 1 час"
    )
    await call.answer()


@dp.callback_query(F.data == "plans")
async def plans(call: CallbackQuery):
    await call.message.edit_text(
        "🎯 Выберите срок подписки:\n\n"
        "💰 Чем дольше — тем выгоднее!",
        reply_markup=plans_kb()
    )
    await call.answer()


@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery):
    await call.message.edit_text(
        "🔓 UNLOCK\n"
        "официальные подписки Spotify\n\n"
        "🎵 ОТКРОЙ МИР МУЗЫКИ С ВЫГОДОЙ\n\n"
        "✅ Официальные подписки\n"
        "⚡ Быстрое подключение\n"
        "🔒 Безопасно и надёжно\n"
        "🆘 Поддержка 24/7",
        reply_markup=start_kb()
    )
    await call.answer()


@dp.callback_query(F.data.startswith("plan:"))
async def choose_plan(call: CallbackQuery):
    key = call.data.split(":")[1]
    name, amount, emoji = PLANS[key]
    order_id = add_order(
        call.from_user.id,
        call.from_user.username or "",
        name,
        amount
    )

    await call.message.edit_text(
        f"{emoji} Подписка: {name}\n"
        f"💰 Стоимость: {amount} ₽\n\n"
        f"💳 Оплата\n"
        f"Переведите {amount} ₽ на карту:\n"
        f"{CARD_NUMBER}\n\n"
        "📸 После перевода нажмите «Я оплатил»\n"
        "и отправьте чек из банка.",
        reply_markup=payment_kb(order_id)
    )
    await call.answer()


@dp.callback_query(F.data.startswith("paid:"))
async def paid(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    order = get_order(order_id)

    if not order or order[1] != call.from_user.id:
        await call.answer("❌ Заказ не найден.", show_alert=True)
        return

    await call.message.answer(
        "📸 Отправьте чек из банка следующим сообщением.\n\n"
        "⏳ После проверки оплаты мы продолжим оформление."
    )
    set_status(order_id, "waiting_receipt")
    await call.answer()


@dp.message(F.photo)
async def receipt(message: Message):
    con = db()
    row = con.execute("""
        SELECT id, plan, amount FROM orders
        WHERE user_id=? AND status='waiting_receipt'
        ORDER BY id DESC LIMIT 1
    """, (message.from_user.id,)).fetchone()
    con.close()

    if not row:
        return

    order_id, plan, amount = row
    set_status(order_id, "checking")

    caption = (
        f"📦 Новый заказ #{order_id}\n\n"
        f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📋 Тариф: {plan}\n"
        f"💰 Сумма: {amount} ₽"
    )

    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=caption,
        reply_markup=admin_payment_kb(order_id)
    )
    await message.answer("✅ Чек получен! Ожидайте проверки оплаты.")


@dp.callback_query(F.data.startswith("approve:"))
async def approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    order_id = int(call.data.split(":")[1])
    order = get_order(order_id)
    if not order:
        await call.answer("❌ Заказ не найден.", show_alert=True)
        return

    set_status(order_id, "waiting_credentials")

    await bot.send_message(
        order[1],
        "✅ Оплата подтверждена!\n\n"
        "🔑 Для подключения отправьте данные аккаунта Spotify.\n"
        "Сообщение будет использовано только для оформления заказа."
    )

    await call.message.edit_caption(
        caption=call.message.caption + "\n\n✅ Статус: ОПЛАТА ПОДТВЕРЖДЕНА"
    )
    await call.answer("✅ Оплата подтверждена.")


@dp.callback_query(F.data.startswith("reject:"))
async def reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    order_id = int(call.data.split(":")[1])
    order = get_order(order_id)
    if not order:
        await call.answer("❌ Заказ не найден.", show_alert=True)
        return

    set_status(order_id, "rejected")

    await bot.send_message(
        order[1],
        "❌ Оплата не подтверждена.\n\n"
        "Проверьте чек и реквизиты.\n"
        "Свяжитесь с поддержкой: " + SUPPORT
    )
    await call.message.edit_caption(
        caption=call.message.caption + "\n\n❌ Статус: ОТКЛОНЕНО"
    )
    await call.answer("❌ Заказ отклонён.")


@dp.message(F.content_type == ContentType.TEXT)
async def credentials(message: Message):
    con = db()
    row = con.execute("""
        SELECT id, plan FROM orders
        WHERE user_id=? AND status='waiting_credentials'
        ORDER BY id DESC LIMIT 1
    """, (message.from_user.id,)).fetchone()
    con.close()

    if not row:
        return

    order_id, plan = row
    set_status(order_id, "credentials_sent")

    await bot.send_message(
        ADMIN_ID,
        f"🔑 Данные для заказа #{order_id}\n\n"
        f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📋 Тариф: {plan}\n\n"
        f"📝 {message.text}"
    )

    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        "✅ Данные получены!\n\n"
        "Заказ передан на подключение.\n"
        "⏳ Ожидайте, скоро всё будет готово!"
    )


async def main():
    if not BOT_TOKEN:
        print("❌ ОШИБКА: Токен не найден в переменных окружения!")
        return
    
    if not ADMIN_ID:
        print("❌ ОШИБКА: ADMIN_ID не найден в переменных окружения!")
        return
    
    print("✅ Бот запущен!")
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"💳 Карта: {CARD_NUMBER}")
    print(f"🆘 Поддержка: {SUPPORT}")
    
    db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
