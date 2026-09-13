from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def categories_keyboard(categories: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=f"{cat['icon']} {cat['name']}", callback_data=f"cat_{cat['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def services_keyboard(category_id: int, services: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    for s in services:
        price_text = f"{int(s['price_per_1000']):,} so'm".replace(",", " ")
        buttons.append([InlineKeyboardButton(
            text=f"{s['name']} | {price_text}", 
            callback_data=f"srv_{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Boshqa tarmoqlar", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def service_action_keyboard(service_id: int, category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Buyurtma berish", callback_data=f"order_{service_id}")],
        [InlineKeyboardButton(text="⬅️ Xizmatlar ro'yxatiga qaytish", callback_data=f"cat_{category_id}")]
    ])

def confirm_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, tasdiqlayman", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_no")]
    ])

def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Balansni to'ldirish", callback_data="topup_balance")],
        [InlineKeyboardButton(text="📋 Buyurtmalar tarixi", callback_data="my_orders_inline")]
    ])

def payment_methods_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ FixHamyon (Avtomatik)", callback_data="pay_fixhamyon")],
        [InlineKeyboardButton(text="💳 Karta orqali (Chek yuborish)", callback_data="pay_card")],
        [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="cancel_pay")]
    ])

# --- VIRTUAL SIM KEYBOARDS ---
def sim_services_keyboard(services: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for s in services:
        row.append(InlineKeyboardButton(text=f"{s['icon']} {s['name']}", callback_data=f"simsrv_{s['code']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="📱 Faol raqamlarim", callback_data="sim_my_active")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sim_countries_keyboard(service: Dict, countries: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    for c in countries:
        price = round(service['base_price_uzs'] * c['price_multiplier'])
        price_text = f"{int(price):,} so'm".replace(",", " ")
        buttons.append([InlineKeyboardButton(
            text=f"{c['icon']} {c['name']} ({c['prefix']}) — {price_text}",
            callback_data=f"simbuy_{service['code']}_{c['code']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Boshqa ilovalar", callback_data="sim_back_services")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sim_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 SMSni tekshirish", callback_data=f"simchk_{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish (Pul qaytariladi)", callback_data=f"simcnc_{order_id}")]
    ])

def sim_active_orders_keyboard(orders: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders:
        buttons.append([InlineKeyboardButton(
            text=f"📱 {o['service_name']} ({o['phone_number']})",
            callback_data=f"simview_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="sim_back_services")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- ADMIN KEYBOARDS ---
def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
         InlineKeyboardButton(text="✉️ Xabarnoma (Rassilka)", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="💰 Balans berish / ayirish", callback_data="adm_balance"),
         InlineKeyboardButton(text="🛠 SMM narxini o'zgartirish", callback_data="adm_prices")],
        [InlineKeyboardButton(text="🌐 SMM API Holati", callback_data="adm_smm_status"),
         InlineKeyboardButton(text="📱 SIM API Holati", callback_data="adm_sim_status")]
    ])

def admin_receipt_keyboard(user_id: int, amount: float, payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash (+Pul qo'shish)", callback_data=f"rec_ok:{payment_id}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rec_no:{payment_id}")]
    ])
