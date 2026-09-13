from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.db import get_or_create_user, get_user, get_user_orders, get_user_all_sim_orders, get_user_referrals_count
from keyboards.reply import get_main_keyboard
from keyboards.inline import profile_keyboard
from config import ADMIN_ID, REFERRAL_BONUS_PERCENT

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Referal ID tekshirish
    referrer_id = 0
    args = message.text.split(maxsplit=1)
    if len(args) == 2 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
        except ValueError:
            referrer_id = 0

    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name,
        referrer_id=referrer_id
    )

    is_admin = (message.from_user.id == ADMIN_ID)
    
    text = (
        f"👋 <b>Assalomu alaykum, {message.from_user.full_name}!</b>\n\n"
        f"<b>RICE SMM BOT</b> ga xush kelibsiz! 🚀\n\n"
        f"Bu yerda siz o'z ijtimoiy tarmoqlaringiz (Telegram, Instagram, TikTok, YouTube va h.k.) "
        f"uchun yuqori sifatli obunachi, layk, ko'rishlar va reaksiyalarni arzon narxlarda xarid qilishingiz mumkin.\n\n"
        f"👇 Kerakli bo'limni tanlang:"
    )
    
    await message.answer(text, reply_markup=get_main_keyboard(is_admin=is_admin), parse_mode="HTML")

@user_router.message(F.text == "❌ Bekor qilish")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("Amal bekor qilindi. Asosiy menyudasiz.", reply_markup=get_main_keyboard(is_admin=is_admin))

@user_router.message(F.text == "👤 Mening hisobim")
async def show_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        user = await get_or_create_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name)
    
    balance_text = f"{int(user['balance']):,} so'm".replace(",", " ")
    spent_text = f"{int(user['spent']):,} so'm".replace(",", " ")
    
    smm_orders = await get_user_orders(message.from_user.id, limit=50)
    sim_orders = await get_user_all_sim_orders(message.from_user.id, limit=50)
    total_orders = len(smm_orders) + len(sim_orders)
    
    text = (
        f"👤 <b>Mening hisobim (Profil)</b>\n\n"
        f"🆔 <b>ID raqam:</b> <code>{user['telegram_id']}</code>\n"
        f"👤 <b>Ism:</b> {user['full_name']}\n"
        f"💰 <b>Asosiy balans:</b> <b>{balance_text}</b>\n"
        f"💸 <b>Jami sarflangan:</b> {spent_text}\n"
        f"📦 <b>Jami buyurtmalar:</b> {total_orders} ta (SMM: {len(smm_orders)}, SIM: {len(sim_orders)})\n\n"
        f"Balansingizni to'ldirish uchun quyidagi tugmani bosing:"
    )
    
    await message.answer(text, reply_markup=profile_keyboard(), parse_mode="HTML")

@user_router.message(F.text == "📋 Buyurtmalarim")
async def show_orders(message: Message):
    smm_orders = await get_user_orders(message.from_user.id, limit=5)
    sim_orders = await get_user_all_sim_orders(message.from_user.id, limit=5)

    if not smm_orders and not sim_orders:
        await message.answer("📭 Sizda hali buyurtmalar mavjud emas.", parse_mode="HTML")
        return
        
    text = "📋 <b>So'nggi buyurtmalaringiz:</b>\n\n"
    
    if sim_orders:
        text += "📱 <b>Virtual SIM raqamlar:</b>\n"
        sim_status = {
            "WAITING_CODE": "🟡 SMS kutilmoqda",
            "RECEIVED": "🟢 Kod qabul qilindi",
            "CANCELED": "🔴 Bekor qilindi"
        }
        for so in sim_orders:
            st = sim_status.get(so['status'], so['status'])
            p_text = f"{int(so['price']):,} so'm".replace(",", " ")
            code_info = f" (Kod: <code>{so['sms_code']}</code>)" if so['sms_code'] else ""
            text += (
                f"🔹 {so['service_name']} | <code>{so['phone_number']}</code>{code_info}\n"
                f"   💵 {p_text} | {st}\n\n"
            )

    if smm_orders:
        text += "🚀 <b>SMM Xizmatlari:</b>\n"
        status_icons = {
            "pending": "🟡 Kutilmoqda",
            "processing": "🔵 Bajarilmoqda",
            "completed": "🟢 Bajarildi",
            "canceled": "🔴 Bekor qilindi",
            "internal_mode": "🟣 Qabul qilindi"
        }
        for o in smm_orders:
            status_label = status_icons.get(o['status'], o['status'])
            price_text = f"{int(o['price']):,} so'm".replace(",", " ")
            text += (
                f"🔹 #{o['id']} {o['service_name']} ({o['quantity']} ta)\n"
                f"   💵 {price_text} | {status_label}\n\n"
            )
        
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text == "👥 Hamkorlik")
async def show_referral(message: Message):
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    ref_count = await get_user_referrals_count(message.from_user.id)
    
    text = (
        f"👥 <b>Hamkorlik (Referal) dasturi</b>\n\n"
        f"Do'stlaringizni taklif qiling va ular hisobini to'ldirganda <b>{REFERRAL_BONUS_PERCENT}%</b> miqdorida "
        f"doimiy bonus (keshbek) oling!\n\n"
        f"🔗 <b>Sizning taklif havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Taklif qilingan do'stlaringiz:</b> {ref_count} ta\n\n"
        f"<i>Havoladan nusxa olib, do'stlaringiz va kanallarga ulashing!</i>"
    )
    
    await message.answer(text, parse_mode="HTML")

@user_router.message(F.text == "ℹ️ Qo'llanma / Aloqa")
async def show_help(message: Message):
    text = (
        f"ℹ️ <b>Qo'llanma va Yordam</b>\n\n"
        f"<b>Qanday buyurtma beriladi?</b>\n"
        f"1. <b>🚀 Buyurtma berish</b> tugmasini bosing.\n"
        f"2. Kerakli ijtimoiy tarmoq va xizmat turini tanlang.\n"
        f"3. Kanal, profil yoki post havolasini (link) yuboring.\n"
        f"4. Miqdorini kiriting va tasdiqlang.\n\n"
        f"⚠️ <i>Diqqat: Buyurtma berishdan oldin profilingiz yoki kanalingiz ommaviy (ochiq / public) ekanligiga ishonch hosil qiling!</i>\n\n"
        f"👨‍💻 <b>Qo'llab-quvvatlash xizmati:</b>\n"
        f"Savol va takliflar bo'yicha adminga murojaat qiling."
    )
    
    await message.answer(text, parse_mode="HTML")
