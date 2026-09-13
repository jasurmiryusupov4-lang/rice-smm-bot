import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.db import (
    get_stats, get_all_users, update_user_balance, get_user,
    get_categories, get_services_by_category, get_service, update_service_price
)
from keyboards.inline import admin_menu_keyboard
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from utils.states import AdminStates
from services.smm_api import smm_client
from services.sms_api import sms_client
from config import ADMIN_ID

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

@admin_router.message(F.text == "⚙️ Admin Panel")
@admin_router.message(Command("admin"))
async def open_admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    text = (
        f"👑 <b>Admin Boshqaruv Paneli</b>\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await message.answer(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")

@admin_router.callback_query(F.data == "adm_stats")
async def show_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    stats = await get_stats()
    vol_text = f"{int(stats['total_volume']):,} so'm".replace(",", " ")
    bal_text = f"{int(stats['total_balance']):,} so'm".replace(",", " ")

    text = (
        f"📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"📦 <b>Jami buyurtmalar:</b> {stats['total_orders']} ta\n"
        f"  ├ 🚀 <b>SMM buyurtmalar:</b> {stats['smm_orders']} ta\n"
        f"  └ 📱 <b>SIM buyurtmalar:</b> {stats['sim_orders']} ta\n"
        f"💵 <b>Umumiy aylanma:</b> {vol_text}\n"
        f"💰 <b>Foydalanuvchilar balansi:</b> {bal_text}\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Admin menyuga qaytish", callback_data="adm_back")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data == "adm_back")
async def back_to_admin_menu(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    await call.message.edit_text(
        "👑 <b>Admin Boshqaruv Paneli</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data == "adm_smm_status")
async def check_smm_api(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    configured = smm_client.is_configured()
    status_text = "🟢 Ulangan" if configured else "🟡 Ichki rejim (API kalit kiritilmagan)"
    
    extra = ""
    if configured:
        bal_res = await smm_client.get_balance()
        extra = f"\n💰 <b>SMM Panel Balansi:</b> {bal_res.get('balance', 'Nomaʼlum')} {bal_res.get('currency', 'USD')}"

    text = (
        f"🌐 <b>SMM Provayder API Holati</b>\n\n"
        f"Holat: <b>{status_text}</b>{extra}\n\n"
        f"<i>SMM Provayder API ni sozlash uchun <code>.env</code> faylida <code>SMM_API_URL</code> va <code>SMM_API_KEY</code> ni to'ldiring.</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data == "adm_sim_status")
async def check_sim_api(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    configured = sms_client.is_configured()
    status_text = "🟢 Ulangan (SMS-Activate)" if configured else "🟡 Demo/Simulyatsiya rejimi"

    extra = ""
    bal_res = await sms_client.get_balance()
    extra = f"\n💰 <b>SMS API Balansi:</b> {bal_res.get('balance', '0.00')} {bal_res.get('currency', 'RUB')}"

    text = (
        f"📱 <b>Virtual SIM (SMS) API Holati</b>\n\n"
        f"Holat: <b>{status_text}</b>{extra}\n\n"
        f"<i>SMS-Activate API kalitini kiritish uchun <code>.env</code> faylida <code>SMS_API_KEY</code> ni to'ldiring.</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

# --- RASSILKA (BROADCAST) ---
@admin_router.callback_query(F.data == "adm_broadcast")
async def start_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminStates.broadcasting)
    await call.message.delete()
    await call.message.answer(
        "✉️ <b>Xabarnoma (Rassilka)</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni (matn, rasm yoki video) yuboring:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.broadcasting)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    users = await get_all_users()
    await message.answer(f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")

    sent = 0
    blocked = 0

    for uid in users:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked += 1

    await state.clear()
    await message.answer(
        f"✅ <b>Xabarnoma yakunlandi!</b>\n\n"
        f"Yuborildi: {sent} ta\n"
        f"Yetib bormadi (bloklagan): {blocked} ta",
        reply_markup=get_main_keyboard(is_admin=True),
        parse_mode="HTML"
    )

# --- BALANS BOSHQARISH ---
@admin_router.callback_query(F.data == "adm_balance")
async def start_balance_adjust(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(AdminStates.adjust_balance_user_id)
    await call.message.delete()
    await call.message.answer(
        "💰 <b>Balans berish / ayirish</b>\n\n"
        "Foydalanuvchining Telegram ID raqamini kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.adjust_balance_user_id)
async def process_balance_user_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqamlardan iborat ID kiriting:")
        return

    uid = int(message.text)
    user = await get_user(uid)
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi. Qaytadan ID kiriting:")
        return

    await state.update_data(target_user_id=uid)
    await state.set_state(AdminStates.adjust_balance_amount)

    balance_text = f"{int(user['balance']):,} so'm".replace(",", " ")
    await message.answer(
        f"👤 Foydalanuvchi: <b>{user['full_name']}</b> (<code>{uid}</code>)\n"
        f"Hozirgi balansi: <b>{balance_text}</b>\n\n"
        f"Qancha summa qo'shmoqchisiz yoki ayirmoqchisiz?\n"
        f"<i>(Qo'shish uchun: <code>50000</code>, ayirish uchun: <code>-20000</code>)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@admin_router.message(AdminStates.adjust_balance_amount)
async def process_balance_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip().replace(" ", "").replace("so'm", "")
    try:
        amount = float(text)
    except ValueError:
        await message.answer("⚠️ Iltimos, to'g'ri son kiriting (masalan: 10000 yoki -5000):")
        return

    data = await state.get_data()
    uid = data["target_user_id"]

    await update_user_balance(uid, amount)
    new_user = await get_user(uid)
    new_bal_text = f"{int(new_user['balance']):,} so'm".replace(",", " ")

    await state.clear()
    await message.answer(
        f"✅ <b>Balans yangilandi!</b>\n\n"
        f"Foydalanuvchi: {new_user['full_name']} (<code>{uid}</code>)\n"
        f"Yangi balans: <b>{new_bal_text}</b>",
        reply_markup=get_main_keyboard(is_admin=True),
        parse_mode="HTML"
    )

    # Foydalanuvchiga xabar berish
    try:
        change_text = f"+{int(amount):,} so'm" if amount > 0 else f"{int(amount):,} so'm"
        await message.bot.send_message(
            chat_id=uid,
            text=f"🔔 <b>Balansingiz o'zgardi!</b>\n\nAdmin tomonidan {change_text} o'zgartirildi.\nYangi balansingiz: <b>{new_bal_text}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

# --- XIZMAT NARXLARINI O'ZGARTIRISH ---
@admin_router.callback_query(F.data == "adm_prices")
async def choose_cat_for_price(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    categories = await get_categories()
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"{cat['icon']} {cat['name']}", callback_data=f"adm_cat_{cat['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back")])

    await call.message.edit_text(
        "🛠 <b>Qaysi tarmoq xizmat narxini o'zgartirmoqchisiz?</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data.startswith("adm_cat_"))
async def choose_srv_for_price(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    cat_id = int(call.data.split("_")[2])
    services = await get_services_by_category(cat_id)

    buttons = []
    for s in services:
        price_text = f"{int(s['price_per_1000']):,} so'm".replace(",", " ")
        buttons.append([InlineKeyboardButton(text=f"{s['name']} ({price_text})", callback_data=f"adm_srv_{s['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_prices")])

    await call.message.edit_text(
        "Xizmatni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(F.data.startswith("adm_srv_"))
async def prompt_new_price(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    srv_id = int(call.data.split("_")[2])
    service = await get_service(srv_id)

    await state.update_data(target_srv_id=srv_id)
    await state.set_state(AdminStates.change_price_val)

    price_text = f"{int(service['price_per_1000']):,} so'm".replace(",", " ")
    await call.message.delete()
    await call.message.answer(
        f"🛠 <b>{service['name']}</b>\n\n"
        f"Hozirgi narxi (1000 ta uchun): <b>{price_text}</b>\n\n"
        f"Yangi narxni so'mda kiriting (Masalan: <code>12000</code>):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(AdminStates.change_price_val)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip().replace(" ", "")
    if not text.isdigit():
        await message.answer("⚠️ Iltimos, musbat raqam kiriting:")
        return

    new_price = float(text)
    data = await state.get_data()
    srv_id = data["target_srv_id"]

    await update_service_price(srv_id, new_price)
    service = await get_service(srv_id)
    price_text = f"{int(service['price_per_1000']):,} so'm".replace(",", " ")

    await state.clear()
    await message.answer(
        f"✅ <b>Xizmat narxi muvaffaqiyatli yangilandi!</b>\n\n"
        f"📌 {service['name']}\n"
        f"💵 Yangi narx: <b>{price_text}</b>",
        reply_markup=get_main_keyboard(is_admin=True),
        parse_mode="HTML"
    )
