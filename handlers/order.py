from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import (
    get_categories, get_category, get_services_by_category, 
    get_service, get_user, update_user_balance, add_user_spent, create_order
)
from keyboards.inline import (
    categories_keyboard, services_keyboard, service_action_keyboard, 
    confirm_order_keyboard, profile_keyboard
)
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from utils.states import OrderStates
from services.smm_api import smm_client
from config import ADMIN_ID

order_router = Router()

@order_router.message(F.text.in_(["🚀 SMM Xizmatlari", "🚀 Buyurtma berish"]))
async def start_order(message: Message, state: FSMContext):
    await state.clear()
    categories = await get_categories()
    if not categories:
        await message.answer("Hozircha xizmatlar mavjud emas.")
        return
        
    await message.answer(
        "🌐 <b>Ijtimoiy tarmoqni tanlang:</b>\n\nQaysi tarmoq uchun xizmat kerak?",
        reply_markup=categories_keyboard(categories),
        parse_mode="HTML"
    )

@order_router.callback_query(F.data == "back_categories")
async def back_to_categories(call: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = await get_categories()
    await call.message.edit_text(
        "🌐 <b>Ijtimoiy tarmoqni tanlang:</b>\n\nQaysi tarmoq uchun xizmat kerak?",
        reply_markup=categories_keyboard(categories),
        parse_mode="HTML"
    )
    await call.answer()

@order_router.callback_query(F.data.startswith("cat_"))
async def select_category(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split("_")[1])
    category = await get_category(cat_id)
    services = await get_services_by_category(cat_id)
    
    if not services:
        await call.answer("Ushbu bo'limda hozircha xizmatlar mavjud emas.", show_alert=True)
        return
        
    await call.message.edit_text(
        f"{category['icon']} <b>{category['name']} xizmatlari:</b>\n\nKerakli xizmat turini tanlang:",
        reply_markup=services_keyboard(cat_id, services),
        parse_mode="HTML"
    )
    await call.answer()

@order_router.callback_query(F.data.startswith("srv_"))
async def select_service(call: CallbackQuery, state: FSMContext):
    srv_id = int(call.data.split("_")[1])
    service = await get_service(srv_id)
    if not service:
        await call.answer("Xizmat topilmadi.", show_alert=True)
        return
        
    price_text = f"{int(service['price_per_1000']):,} so'm".replace(",", " ")
    min_amount = f"{service['min_amount']:,}".replace(",", " ")
    max_amount = f"{service['max_amount']:,}".replace(",", " ")
    
    text = (
        f"📌 <b>Xizmat:</b> {service['name']}\n"
        f"📝 <b>Tavsif:</b> {service['description'] or 'Yuqori sifat'}\n"
        f"💵 <b>Narxi:</b> 1 000 ta uchun <b>{price_text}</b>\n"
        f"🔻 <b>Minimal:</b> {min_amount} ta\n"
        f"🔺 <b>Maksimal:</b> {max_amount} ta\n\n"
        f"Buyurtma berishni istaysizmi?"
    )
    
    await call.message.edit_text(
        text,
        reply_markup=service_action_keyboard(service['id'], service['category_id']),
        parse_mode="HTML"
    )
    await call.answer()

@order_router.callback_query(F.data.startswith("order_"))
async def prompt_link(call: CallbackQuery, state: FSMContext):
    srv_id = int(call.data.split("_")[1])
    service = await get_service(srv_id)
    if not service:
        await call.answer("Xizmat topilmadi.", show_alert=True)
        return

    await state.update_data(service_id=srv_id)
    await state.set_state(OrderStates.entering_link)
    
    await call.message.delete()
    await call.message.answer(
        f"🔗 <b>{service['name']}</b>\n\n"
        f"Iltimos, buyurtma uchun havola (link) yuboring:\n"
        f"<i>(Masalan: kanal, profil yoki post havolasi)</i>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@order_router.message(OrderStates.entering_link)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://") or link.startswith("t.me/") or link.startswith("@")):
        await message.answer("⚠️ Iltimos, to'g'ri havola (link) yuboring!\nMasalan: https://t.me/kanal_nomi yoki https://instagram.com/profil")
        return
        
    data = await state.get_data()
    service = await get_service(data['service_id'])
    
    await state.update_data(link=link)
    await state.set_state(OrderStates.entering_quantity)
    
    await message.answer(
        f"🔢 Endi kerakli <b>miqdorni</b> kiriting:\n\n"
        f"Minimal: <b>{service['min_amount']}</b> ta\n"
        f"Maksimal: <b>{service['max_amount']}</b> ta",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@order_router.message(OrderStates.entering_quantity)
async def process_quantity(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ Iltimos, faqat musbat raqam kiriting (masalan: 1000):")
        return
        
    quantity = int(text)
    data = await state.get_data()
    service = await get_service(data['service_id'])
    
    if quantity < service['min_amount']:
        await message.answer(f"⚠️ Minimal miqdor: {service['min_amount']} ta. Qaytadan kiriting:")
        return
        
    if quantity > service['max_amount']:
        await message.answer(f"⚠️ Maksimal miqdor: {service['max_amount']} ta. Qaytadan kiriting:")
        return
        
    # Narxni hisoblash
    total_price = round((quantity / 1000.0) * service['price_per_1000'], 2)
    price_text = f"{int(total_price):,} so'm".replace(",", " ")
    
    await state.update_data(quantity=quantity, total_price=total_price)
    await state.set_state(OrderStates.confirming_order)
    
    confirm_text = (
        f"🧾 <b>Buyurtmani tasdiqlaysizmi?</b>\n\n"
        f"📌 <b>Xizmat:</b> {service['name']}\n"
        f"🔗 <b>Havola:</b> {data['link']}\n"
        f"🔢 <b>Miqdor:</b> {quantity} ta\n"
        f"💵 <b>Jami summa:</b> <b>{price_text}</b>\n\n"
        f"Tasdiqlaysizmi?"
    )
    
    await message.answer(confirm_text, reply_markup=confirm_order_keyboard(), parse_mode="HTML")

@order_router.callback_query(OrderStates.confirming_order, F.data == "confirm_yes")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_user(call.from_user.id)
    service = await get_service(data['service_id'])
    
    total_price = data['total_price']
    
    # Balansni tekshirish
    if user['balance'] < total_price:
        needed = total_price - user['balance']
        needed_text = f"{int(needed):,} so'm".replace(",", " ")
        balance_text = f"{int(user['balance']):,} so'm".replace(",", " ")
        
        await call.message.delete()
        await call.message.answer(
            f"❌ <b>Hisobingizda mablag' yetarli emas!</b>\n\n"
            f"💰 Sizning balansingiz: <b>{balance_text}</b>\n"
            f"💳 Yetishmayotgan summa: <b>{needed_text}</b>\n\n"
            f"Iltimos, avval hisobingizni to'ldiring:",
            reply_markup=profile_keyboard(),
            parse_mode="HTML"
        )
        await state.clear()
        await call.answer()
        return

    # Balansdan yechish
    await update_user_balance(call.from_user.id, -total_price)
    await add_user_spent(call.from_user.id, total_price)
    
    # SMM API orqali provayderga jo'natish
    smm_resp = await smm_client.add_order(service['smm_service_id'], data['link'], data['quantity'])
    smm_order_id = smm_resp.get("order", 0) if isinstance(smm_resp, dict) else 0
    status = "processing" if smm_order_id else "internal_mode"

    # Bazaga yozish
    order_id = await create_order(
        user_id=call.from_user.id,
        service_id=service['id'],
        service_name=service['name'],
        link=data['link'],
        quantity=data['quantity'],
        price=total_price,
        smm_order_id=smm_order_id,
        status=status
    )
    
    price_text = f"{int(total_price):,} so'm".replace(",", " ")
    is_admin = (call.from_user.id == ADMIN_ID)
    
    await call.message.delete()
    await call.message.answer(
        f"✅ <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🆔 <b>Buyurtma ID:</b> #{order_id}\n"
        f"📌 <b>Xizmat:</b> {service['name']}\n"
        f"🔗 <b>Havola:</b> {data['link']}\n"
        f"🔢 <b>Miqdor:</b> {data['quantity']} ta\n"
        f"💵 <b>To'langan:</b> {price_text}\n"
        f"📊 <b>Holati:</b> Jarayonda\n\n"
        f"Xizmat tez orada bajariladi. Buyurtma holatini <b>📋 Buyurtmalarim</b> bo'limida kuzatishingiz mumkin.",
        reply_markup=get_main_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

    # Adminga xabar berish
    try:
        await call.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Yangi buyurtma!</b>\n\n"
            f"🆔 <b>Buyurtma:</b> #{order_id}\n"
            f"👤 <b>Foydalanuvchi:</b> {call.from_user.full_name} (ID: <code>{call.from_user.id}</code>)\n"
            f"📌 <b>Xizmat:</b> {service['name']}\n"
            f"🔗 <b>Havola:</b> {data['link']}\n"
            f"🔢 <b>Miqdor:</b> {data['quantity']} ta\n"
            f"💵 <b>Summa:</b> {price_text}\n"
            f"🌐 <b>SMM ID:</b> {smm_order_id or 'Ichki rejim'}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()
    await call.answer()

@order_router.callback_query(OrderStates.confirming_order, F.data == "confirm_no")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == ADMIN_ID)
    await call.message.delete()
    await call.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_main_keyboard(is_admin=is_admin))
    await call.answer()
