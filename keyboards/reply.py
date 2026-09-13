from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="📱 Virtual raqamlar (SMS)"), KeyboardButton(text="🚀 SMM Xizmatlari")],
        [KeyboardButton(text="👤 Mening hisobim"), KeyboardButton(text="📋 Buyurtmalarim")],
        [KeyboardButton(text="👥 Hamkorlik"), KeyboardButton(text="ℹ️ Qo'llanma / Aloqa")]
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )
