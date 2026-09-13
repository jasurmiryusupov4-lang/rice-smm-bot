import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.db import create_payment, complete_payment, get_db
from keyboards.inline import payment_methods_keyboard, admin_receipt_keyboard
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from utils.states import PaymentStates
from services.fixhamyon import fixhamyon_service
from config import ADMIN_ID

payment_router = Router()

@payment_router.callback_query(F.data == "topup_balance")
async def start_topup(call: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentStates.entering_amount)
    await call.message.delete()
    await call.message.answer(
        "💳 <b>Balansni to'ldirish</b>\n\n"
        "Iltimos, hisobingizga qancha mablag' kiritmoqchisiz?\n"
        "<i>(Minimal summa: 5 000 so'm)</i>\n\n"
        "Summani raqamda kiriting (Masalan: <code>25000</code>):",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await call.answer()

@payment_router.message(PaymentStates.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    text = message.text.strip().replace(" ", "").replace("so'm", "").replace("som", "")
    if not text.isdigit():
        await message.answer("⚠️ Iltimos, faqat musbat son kiriting (masalan: 20000):")
        return
        
    amount = float(text)
    if amount < 5000:
        await message.answer("⚠️ Minimal to'ldirish summasi: 5 000 so'm. Qaytadan kiriting:")
        return

    await state.update_data(amount=amount)
    amount_text = f"{int(amount):,} so'm".replace(",", " ")
    
    await message.answer(
        f"💳 To'ldirish summasi: <b>{amount_text}</b>\n\n"
        f"To'lov turini tanlang:",
        reply_markup=payment_methods_keyboard(),
        parse_mode="HTML"
    )

@payment_router.callback_query(F.data == "cancel_pay")
async def cancel_payment_flow(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = (call.from_user.id == ADMIN_ID)
    await call.message.delete()
    await call.message.answer("To'lov bekor qilindi.", reply_markup=get_main_keyboard(is_admin=is_admin))
    await call.answer()

@payment_router.callback_query(F.data == "pay_fixhamyon")
async def pay_via_fixhamyon(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount", 10000)
    
    invoice = fixhamyon_service.create_invoice(call.from_user.id, amount)
    payment_id = invoice["payment_id"]
    
    await create_payment(call.from_user.id, amount, "fixhamyon", payment_id)
    
    amount_text = f"{int(amount):,} so'm".replace(",", " ")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 FixHamyon orqali to'lash", url=invoice["url"])],
        [InlineKeyboardButton(text="🔄 To'lovni tekshirish", callback_data=f"chk_fix:{payment_id}")],
        [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="cancel_pay")]
    ])
    
    await call.message.edit_text(
        f"⚡ <b>FixHamyon orqali to'lov</b>\n\n"
        f"💵 <b>To'lov summasi:</b> {amount_text}\n"
        f"🆔 <b>To'lov ID:</b> <code>{payment_id}</code>\n\n"
        f"Pastdagi tugma orqali @FixHamyonBot ga o'tib to'lovni amalga oshiring. To'lov qilingach <b>To'lovni tekshirish</b> tugmasini bosing:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.clear()
    await call.answer()

@payment_router.callback_query(F.data.startswith("chk_fix:"))
async def check_fixhamyon_payment(call: CallbackQuery):
    payment_id = call.data.split(":")[1]
    
    # To'lovni tekshirish
    async with get_db() as db:
        c = await db.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
        p = await c.fetchone()
        
    if p and p["status"] == "completed":
        await call.answer("✅ To'lovingiz tasdiqlangan va balansingizga qo'shilgan!", show_alert=True)
        return
        
    # Hozircha to'lov o'tmagan bo'lsa
    await call.answer("⏳ To'lov hali qabul qilinmadi yoki tizimda kutilmoqda. Iltimos, to'lovni yakunlab qayta urinib ko'ring.", show_alert=True)

@payment_router.callback_query(F.data == "pay_card")
async def pay_via_card(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount", 10000)
    amount_text = f"{int(amount):,} so'm".replace(",", " ")
    
    await state.set_state(PaymentStates.waiting_receipt)
    
    await call.message.edit_text(
        f"💳 <b>Karta orqali to'lov (Chek yuborish)</b>\n\n"
        f"To'lov summasi: <b>{amount_text}</b>\n\n"
        f"Kartamiz raqami: <code>9860 3501 **** ****</code> (Admin)\n\n"
        f"1. Yuqoridagi kartaga to'lovni o'tkazing.\n"
        f"2. To'lov <b>chekining rasmini (skrinshotini)</b> shu botga yuboring.\n\n"
        f"Chek tekshirilishi bilan hisobingiz to'ldiriladi!",
        parse_mode="HTML"
    )
    await call.answer()

@payment_router.message(PaymentStates.waiting_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount", 0)
    amount_text = f"{int(amount):,} so'm".replace(",", " ")
    
    payment_id = f"REC_{message.from_user.id}_{int(amount)}_{uuid.uuid4().hex[:6]}"
    await create_payment(message.from_user.id, amount, "card_receipt", payment_id)
    
    # Adminga chekni yuborish
    photo_id = message.photo[-1].file_id
    caption = (
        f"🧾 <b>Yangi to'lov cheki!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name} (ID: <code>{message.from_user.id}</code>)\n"
        f"💵 <b>Summa:</b> {amount_text}\n"
        f"🆔 <b>To'lov ID:</b> <code>{payment_id}</code>"
    )
    
    try:
        await message.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=caption,
            reply_markup=admin_receipt_keyboard(message.from_user.id, amount, payment_id),
            parse_mode="HTML"
        )
    except Exception as e:
        pass
        
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "Admin chekni tekshirishi bilan balansingizga mablag' qo'shiladi va sizga xabar keladi.",
        reply_markup=get_main_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )

@payment_router.callback_query(F.data.startswith("rec_ok:"))
async def approve_receipt(call: CallbackQuery):
    payment_id = call.data.split(":", 1)[1]
    res = await complete_payment(payment_id)
    
    if not res:
        await call.answer("Ushbu to'lov allaqachon tasdiqlangan yoki topilmadi.", show_alert=True)
        return
        
    amount_text = f"{int(res['amount']):,} so'm".replace(",", " ")
    await call.message.edit_caption(
        caption=f"{call.message.caption}\n\n🟢 <b>TASDIQLANDI (+{amount_text})</b>",
        parse_mode="HTML"
    )
    
    # Foydalanuvchiga xabar
    try:
        await call.bot.send_message(
            chat_id=res["user_id"],
            text=f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                 f"Balansingizga <b>+{amount_text}</b> qo'shildi. "
                 f"Xizmatlardan bemalol foydalanishingiz mumkin!",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    await call.answer("To'lov tasdiqlandi!")

@payment_router.callback_query(F.data.startswith("rec_no:"))
async def reject_receipt(call: CallbackQuery):
    payment_id = call.data.split(":", 1)[1]
    
    async with get_db() as db:
        await db.execute("UPDATE payments SET status = 'rejected' WHERE payment_id = ?", (payment_id,))
        c = await db.execute("SELECT user_id, amount FROM payments WHERE payment_id = ?", (payment_id,))
        p = await c.fetchone()
        await db.commit()
        
    await call.message.edit_caption(
        caption=f"{call.message.caption}\n\n🔴 <b>RAD ETILDI</b>",
        parse_mode="HTML"
    )
    
    if p:
        try:
            await call.bot.send_message(
                chat_id=p["user_id"],
                text="❌ <b>To'lovingiz rad etildi!</b>\n\nIltimos, ma'lumotlarni tekshirib admin bilan bog'laning.",
                parse_mode="HTML"
            )
        except Exception:
            pass
            
    await call.answer("To'lov rad etildi.")
