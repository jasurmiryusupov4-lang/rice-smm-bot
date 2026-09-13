import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_sim_services, get_sim_service, get_sim_countries, get_sim_country,
    get_user, update_user_balance, add_user_spent, create_sim_order,
    get_sim_order, get_user_active_sim_orders, update_sim_order_status,
    cancel_sim_order_and_refund
)
from keyboards.inline import (
    sim_services_keyboard, sim_countries_keyboard, sim_order_keyboard,
    sim_active_orders_keyboard, profile_keyboard
)
from keyboards.reply import get_main_keyboard
from services.sms_api import sms_client
from config import ADMIN_ID

logger = logging.getLogger(__name__)
sim_router = Router()

@sim_router.message(F.text == "📱 Virtual raqamlar (SMS)")
async def show_sim_services(message: Message, state: FSMContext):
    await state.clear()
    services = await get_sim_services()
    if not services:
        await message.answer("Hozircha virtual raqam xizmatlari mavjud emas.")
        return

    text = (
        f"📱 <b>Virtual Raqamlar (SMS qabul qilish)</b>\n\n"
        f"Qaysi dastur yoki ijtimoiy tarmoq uchun raqam kerak?\n"
        f"Kerakli xizmatni tanlang:"
    )
    await message.answer(text, reply_markup=sim_services_keyboard(services), parse_mode="HTML")

@sim_router.callback_query(F.data == "sim_back_services")
async def back_to_sim_services(call: CallbackQuery, state: FSMContext):
    await state.clear()
    services = await get_sim_services()
    text = (
        f"📱 <b>Virtual Raqamlar (SMS qabul qilish)</b>\n\n"
        f"Qaysi dastur yoki ijtimoiy tarmoq uchun raqam kerak?\n"
        f"Kerakli xizmatni tanlang:"
    )
    await call.message.edit_text(text, reply_markup=sim_services_keyboard(services), parse_mode="HTML")
    await call.answer()

@sim_router.callback_query(F.data.startswith("simsrv_"))
async def select_sim_service(call: CallbackQuery):
    service_code = call.data.split("_")[1]
    service = await get_sim_service(service_code)
    if not service:
        await call.answer("Xizmat topilmadi.", show_alert=True)
        return

    countries = await get_sim_countries()
    text = (
        f"{service['icon']} <b>{service['name']} uchun virtual raqam:</b>\n\n"
        f"Kerakli davlatni tanlang (narxlar ko'rsatilgan):"
    )
    await call.message.edit_text(text, reply_markup=sim_countries_keyboard(service, countries), parse_mode="HTML")
    await call.answer()

@sim_router.callback_query(F.data.startswith("simbuy_"))
async def buy_sim_number(call: CallbackQuery):
    parts = call.data.split("_")
    service_code = parts[1]
    country_code = parts[2]

    service = await get_sim_service(service_code)
    country = await get_sim_country(country_code)

    if not service or not country:
        await call.answer("Ma'lumotlar topilmadi.", show_alert=True)
        return

    price = round(service['base_price_uzs'] * country['price_multiplier'])
    user = await get_user(call.from_user.id)

    # Balansni tekshirish
    if user['balance'] < price:
        needed = price - user['balance']
        needed_text = f"{int(needed):,} so'm".replace(",", " ")
        bal_text = f"{int(user['balance']):,} so'm".replace(",", " ")
        
        await call.message.delete()
        await call.message.answer(
            f"❌ <b>Hisobingizda mablag' yetarli emas!</b>\n\n"
            f"Raqam narxi: <b>{int(price):,} so'm</b>\n"
            f"Sizning balansingiz: <b>{bal_text}</b>\n"
            f"Yetishmayotgan summa: <b>{needed_text}</b>\n\n"
            f"Iltimos, avval hisobingizni to'ldiring:",
            reply_markup=profile_keyboard(),
            parse_mode="HTML"
        )
        await call.answer()
        return

    await call.message.edit_text("⏳ <i>Virtual raqam olinmoqda, iltimos kuting...</i>", parse_mode="HTML")

    # Provayderdan raqam olish
    resp = await sms_client.get_number(service_code, country['country_id'], country['prefix'])
    if not resp.get("ok"):
        error_msg = resp.get("error", "Raqamlar qolmagan")
        if "NO_NUMBERS" in error_msg:
            error_msg = "Ushbu davlat bo'yicha hozircha bo'sh raqam qolmagan. Boshqa davlatni tanlang."
        elif "NO_BALANCE" in error_msg:
            error_msg = "SMS provayderda mablag' yetarli emas. Admin bilan bog'laning."

        await call.message.edit_text(f"⚠️ <b>Xatolik yuz berdi:</b>\n{error_msg}", parse_mode="HTML")
        await call.answer()
        return

    # Balansdan yechish
    await update_user_balance(call.from_user.id, -price)
    await add_user_spent(call.from_user.id, price)

    phone = resp["phone"]
    provider_id = resp["provider_id"]

    order_id = await create_sim_order(
        user_id=call.from_user.id,
        phone_number=phone,
        provider_order_id=provider_id,
        service_code=service['code'],
        service_name=service['name'],
        country_code=country['code'],
        country_name=country['name'],
        price=price
    )

    price_text = f"{int(price):,} so'm".replace(",", " ")
    text = (
        f"📱 <b>Yangi virtual raqam olindi!</b>\n\n"
        f"📌 <b>Xizmat:</b> {service['name']} {service['icon']}\n"
        f"🌍 <b>Davlat:</b> {country['name']} {country['icon']}\n"
        f"📞 <b>Raqam:</b> <code>{phone}</code> <i>(nusxa olish uchun ustiga bosing)</i>\n"
        f"💵 <b>Narxi:</b> {price_text}\n"
        f"⏱ <b>Vaqt:</b> 15 daqiqa\n\n"
        f"📩 <b>SMS holati:</b> <i>Kod kutilmoqda...</i>\n\n"
        f"⚠️ <i>Agar kod kelmasa, 'Bekor qilish' tugmasini bosing — pul to'liq balansingizga qaytariladi!</i>"
    )

    await call.message.edit_text(text, reply_markup=sim_order_keyboard(order_id), parse_mode="HTML")
    await call.answer()

@sim_router.callback_query(F.data.startswith("simchk_"))
async def check_sms_status(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    order = await get_sim_order(order_id)

    if not order:
        await call.answer("Buyurtma topilmadi.", show_alert=True)
        return

    if order["status"] == "RECEIVED":
        await call.answer(f"✅ Kod allaqachon olingan: {order['sms_code']}", show_alert=True)
        return

    if order["status"] == "CANCELED":
        await call.answer("Ushbu raqam bekor qilingan.", show_alert=True)
        return

    status_resp = await sms_client.get_status(order["provider_order_id"])
    st = status_resp.get("status")

    if st == "OK":
        code = status_resp.get("code", "")
        await update_sim_order_status(order_id, "RECEIVED", sms_code=code, sms_text=f"Kod: {code}")
        await sms_client.set_status(order["provider_order_id"], 6)

        text = (
            f"🎉 <b>SMS KODI QABUL QILINDI!</b>\n\n"
            f"📌 <b>Xizmat:</b> {order['service_name']}\n"
            f"📞 <b>Raqam:</b> <code>{order['phone_number']}</code>\n"
            f"🔑 <b>SMS Kod:</b> <code>{code}</code> <i>(nusxa olish uchun ustiga bosing)</i>\n\n"
            f"✅ Faollashtirish muvaffaqiyatli yakunlandi!"
        )
        await call.message.edit_text(text, parse_mode="HTML")
        await call.answer("SMS kod qabul qilindi!")
    elif st == "CANCEL":
        await cancel_sim_order_and_refund(order_id)
        await call.message.edit_text(
            f"❌ <b>Raqam bekor qilindi.</b>\n\nMablag' ({int(order['price']):,} so'm) balansingizga qaytarildi.",
            parse_mode="HTML"
        )
        await call.answer("Raqam bekor qilingan.")
    else:
        await call.answer("⏳ SMS kodi hali kelmadi. Iltimos kuting yoki 1-2 daqiqadan so'ng qayta tekshiring.", show_alert=True)

@sim_router.callback_query(F.data.startswith("simcnc_"))
async def cancel_sim_number(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    order = await get_sim_order(order_id)

    if not order or order["status"] != "WAITING_CODE":
        await call.answer("Ushbu raqamni bekor qilib bo'lmaydi.", show_alert=True)
        return

    # Provayderda bekor qilish (status 8)
    await sms_client.set_status(order["provider_order_id"], 8)

    # Pulni balansga qaytarish
    refunded = await cancel_sim_order_and_refund(order_id)
    if refunded:
        price_text = f"{int(order['price']):,} so'm".replace(",", " ")
        text = (
            f"❌ <b>Raqam bekor qilindi!</b>\n\n"
            f"📞 Raqam: <code>{order['phone_number']}</code>\n"
            f"💰 <b>{price_text}</b> to'liq balansingizga qaytarildi."
        )
        await call.message.edit_text(text, parse_mode="HTML")
        await call.answer("Raqam bekor qilindi va pulingiz qaytarildi!")
    else:
        await call.answer("Xatolik yuz berdi.", show_alert=True)

@sim_router.callback_query(F.data == "sim_my_active")
async def show_my_active_numbers(call: CallbackQuery):
    orders = await get_user_active_sim_orders(call.from_user.id)
    if not orders:
        await call.answer("Sizda hozircha faol kutilayotgan raqamlar yo'q.", show_alert=True)
        return

    text = "📱 <b>Sizning faol (kutilayotgan) raqamlaringiz:</b>\n\nKerakli raqamni tanlang:"
    await call.message.edit_text(text, reply_markup=sim_active_orders_keyboard(orders), parse_mode="HTML")
    await call.answer()

@sim_router.callback_query(F.data.startswith("simview_"))
async def view_sim_order(call: CallbackQuery):
    order_id = int(call.data.split("_")[1])
    order = await get_sim_order(order_id)
    if not order:
        await call.answer("Raqam topilmadi.", show_alert=True)
        return

    price_text = f"{int(order['price']):,} so'm".replace(",", " ")
    text = (
        f"📱 <b>Virtual Raqam #{order['id']}</b>\n\n"
        f"📌 <b>Xizmat:</b> {order['service_name']}\n"
        f"🌍 <b>Davlat:</b> {order['country_name']}\n"
        f"📞 <b>Raqam:</b> <code>{order['phone_number']}</code>\n"
        f"💵 <b>Narxi:</b> {price_text}\n"
        f"📊 <b>Holati:</b> Kod kutilmoqda...\n"
    )
    await call.message.edit_text(text, reply_markup=sim_order_keyboard(order_id), parse_mode="HTML")
    await call.answer()
