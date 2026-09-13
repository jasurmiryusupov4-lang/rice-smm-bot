import aiosqlite
import logging
from contextlib import asynccontextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    async with get_db() as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0.0,
            spent REAL DEFAULT 0.0,
            referrer_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📱',
            order_index INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price_per_1000 REAL NOT NULL,
            min_amount INTEGER NOT NULL DEFAULT 10,
            max_amount INTEGER NOT NULL DEFAULT 50000,
            smm_service_id INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            link TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            smm_order_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
        """)

        # Virtual SIM jadvallari
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sim_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📱',
            base_price_uzs REAL NOT NULL,
            order_index INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS sim_countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            country_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '🌐',
            prefix TEXT NOT NULL,
            price_multiplier REAL DEFAULT 1.0,
            order_index INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS sim_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            phone_number TEXT NOT NULL,
            provider_order_id TEXT NOT NULL,
            service_code TEXT NOT NULL,
            service_name TEXT NOT NULL,
            country_code TEXT NOT NULL,
            country_name TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'WAITING_CODE',
            sms_code TEXT DEFAULT '',
            sms_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_system TEXT NOT NULL,
            payment_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        await db.commit()

    # Standart xizmatlar va SIM ma'lumotlarini kiritish
    await seed_default_data()
    await seed_default_sim_data()

async def seed_default_data():
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM categories")
        row = await cursor.fetchone()
        if row and row["count"] > 0:
            return

        categories = [
            (1, "Telegram", "✈️", 1),
            (2, "Instagram", "📷", 2),
            (3, "TikTok", "🎵", 3),
            (4, "YouTube", "🎬", 4),
            (5, "Facebook", "📘", 5),
        ]
        await db.executemany("INSERT INTO categories (id, name, icon, order_index) VALUES (?, ?, ?, ?)", categories)

        services = [
            (1, "Obunachi (O'zbek / Kafolatsiz)", "Tezkor a'zolar qo'shish", 8000.0, 50, 20000, 101),
            (1, "Obunachi (Kafolatli / 30 kun)", "Sifatli obunachilar, to'kilmaydi", 15000.0, 50, 50000, 102),
            (1, "Post ko'rish (So'nggi 1 ta post)", "Tezkor ko'rishlar", 800.0, 100, 100000, 103),
            (1, "Post ko'rish (So'nggi 10 ta post)", "Barcha postlarga avto ko'rish", 6000.0, 100, 100000, 104),
            (1, "Reaksiyalar (Mix / Ijobiy)", "Postlarga 👍🔥❤️ reaksiyalar", 1500.0, 50, 50000, 105),

            (2, "Obunachi (Tezkor / Mix)", "Tez qo'shiluvchi obunachilar", 9000.0, 50, 30000, 201),
            (2, "Obunachi (Kafolatli / 30 kun)", "To'kilish kam, 30 kun kafolat", 18000.0, 50, 50000, 202),
            (2, "Layklar (Tezkor)", "Postlarga sifatli layklar", 2500.0, 50, 50000, 203),
            (2, "Ko'rishlar (Reels / Video)", "Reels tavsiyaga chiqishiga yordam beradi", 1200.0, 100, 100000, 204),
            (2, "Kommentariya (O'zbek / Ijobiy)", "Jonli o'zbekcha izohlar", 45000.0, 10, 1000, 205),

            (3, "Obunachilar (Tezkor)", "TikTok akkaunt uchun obunachilar", 14000.0, 50, 20000, 301),
            (3, "Layklar", "Videolarga layklar", 4000.0, 50, 50000, 302),
            (3, "Video ko'rishlar", "Rekomendatsiya (Tavsiya) ko'rishlari", 500.0, 500, 100000, 303),
            (3, "Ulashishlar (Shares)", "Video ko'proq tarqalishi uchun", 3000.0, 50, 50000, 304),

            (4, "Obunachilar (Kafolatli)", "YouTube kanali uchun sifatli obunachilar", 70000.0, 50, 5000, 401),
            (4, "Video ko'rishlar", "YouTube tavsiyalariga chiqish", 18000.0, 500, 50000, 402),
            (4, "Layklar", "Videolarga layklar", 12000.0, 50, 20000, 403),

            (5, "Sahifa yoqtirishlari (Likes)", "Sahifa obunachilari va layklari", 25000.0, 50, 10000, 501),
            (5, "Post layklari", "Postlarga layklar", 8000.0, 50, 20000, 502),
        ]

        await db.executemany("""
        INSERT INTO services (category_id, name, description, price_per_1000, min_amount, max_amount, smm_service_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, services)

        await db.commit()

async def seed_default_sim_data():
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM sim_services")
        row = await cursor.fetchone()
        if row and row["count"] > 0:
            return

        sim_services = [
            ("tg", "Telegram", "✈️", 12000.0, 1),
            ("wa", "WhatsApp", "💬", 14000.0, 2),
            ("ig", "Instagram", "📷", 6000.0, 3),
            ("lf", "TikTok", "🎵", 5000.0, 4),
            ("dr", "ChatGPT / OpenAI", "🤖", 11000.0, 5),
            ("go", "Google / Gmail", "🔍", 8000.0, 6),
            ("vk", "VKontakte", "🔵", 9000.0, 7),
            ("ds", "Discord", "🎮", 7000.0, 8),
            ("mt", "Steam", "🕹", 7000.0, 9),
            ("tw", "Twitter / X", "🐦", 8000.0, 10),
            ("ot", "Boshqa xizmatlar", "🌐", 7000.0, 11),
        ]
        await db.executemany("""
        INSERT INTO sim_services (code, name, icon, base_price_uzs, order_index)
        VALUES (?, ?, ?, ?, ?)
        """, sim_services)

        sim_countries = [
            ("ru", 0, "Rossiya", "🇷🇺", "+7", 1.0, 1),
            ("us", 12, "AQSH", "🇺🇸", "+1", 1.2, 2),
            ("kz", 2, "Qozog'iston", "🇰🇿", "+77", 1.1, 3),
            ("gb", 16, "Buyuk Britaniya", "🇬🇧", "+44", 1.3, 4),
            ("id", 6, "Indoneziya", "🇮🇩", "+62", 0.9, 5),
            ("uz", 40, "O'zbekiston", "🇺🇿", "+998", 1.8, 6),
            ("kg", 11, "Qirg'iziston", "🇰🇬", "+996", 1.1, 7),
            ("tr", 62, "Turkiya", "🇹🇷", "+90", 1.2, 8),
            ("br", 73, "Braziliya", "🇧🇷", "+55", 1.0, 9),
            ("ca", 36, "Kanada", "🇨🇦", "+1", 1.3, 10),
        ]
        await db.executemany("""
        INSERT INTO sim_countries (code, country_id, name, icon, prefix, price_multiplier, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sim_countries)

        await db.commit()

async def get_or_create_user(telegram_id: int, username: str, full_name: str, referrer_id: int = 0):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await cursor.fetchone()
        if user:
            await db.execute("UPDATE users SET username = ?, full_name = ? WHERE telegram_id = ?", 
                             (username, full_name, telegram_id))
            await db.commit()
            return dict(user)

        if referrer_id == telegram_id:
            referrer_id = 0

        await db.execute("""
        INSERT INTO users (telegram_id, username, full_name, referrer_id)
        VALUES (?, ?, ?, ?)
        """, (telegram_id, username, full_name, referrer_id))
        await db.commit()

        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        new_user = await cursor.fetchone()
        return dict(new_user)

async def get_user(telegram_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_user_balance(telegram_id: int, amount_delta: float):
    async with get_db() as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount_delta, telegram_id))
        await db.commit()

async def add_user_spent(telegram_id: int, amount: float):
    async with get_db() as db:
        await db.execute("UPDATE users SET spent = spent + ? WHERE telegram_id = ?", (amount, telegram_id))
        await db.commit()

# --- SMM Xizmatlar ---
async def get_categories():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM categories ORDER BY order_index ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_category(category_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_services_by_category(category_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM services WHERE category_id = ? AND is_active = 1", (category_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_service(service_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_order(user_id: int, service_id: int, service_name: str, link: str, quantity: int, price: float, smm_order_id: int = 0, status: str = "pending"):
    async with get_db() as db:
        cursor = await db.execute("""
        INSERT INTO orders (user_id, service_id, service_name, link, quantity, price, smm_order_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, service_id, service_name, link, quantity, price, smm_order_id, status))
        order_id = cursor.lastrowid
        await db.commit()
        return order_id

async def get_user_orders(user_id: int, limit: int = 10):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

# --- VIRTUAL SIM FUNCTIONS ---
async def get_sim_services():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_services ORDER BY order_index ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_sim_service(code: str):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_services WHERE code = ?", (code,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_sim_countries():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_countries ORDER BY order_index ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_sim_country(code: str):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_countries WHERE code = ?", (code,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_sim_order(user_id: int, phone_number: str, provider_order_id: str, service_code: str, service_name: str, country_code: str, country_name: str, price: float):
    async with get_db() as db:
        cursor = await db.execute("""
        INSERT INTO sim_orders (user_id, phone_number, provider_order_id, service_code, service_name, country_code, country_name, price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'WAITING_CODE')
        """, (user_id, phone_number, provider_order_id, service_code, service_name, country_code, country_name, price))
        order_id = cursor.lastrowid
        await db.commit()
        return order_id

async def get_sim_order(order_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user_active_sim_orders(user_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_orders WHERE user_id = ? AND status = 'WAITING_CODE' ORDER BY id DESC", (user_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_user_all_sim_orders(user_id: int, limit: int = 10):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_all_waiting_sim_orders():
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_orders WHERE status = 'WAITING_CODE'")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def update_sim_order_status(order_id: int, status: str, sms_code: str = "", sms_text: str = ""):
    async with get_db() as db:
        await db.execute("""
        UPDATE sim_orders 
        SET status = ?, sms_code = ?, sms_text = ? 
        WHERE id = ?
        """, (status, sms_code, sms_text, order_id))
        await db.commit()

async def cancel_sim_order_and_refund(order_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM sim_orders WHERE id = ?", (order_id,))
        order = await cursor.fetchone()
        if not order or order["status"] != "WAITING_CODE":
            return False

        # Statusini CANCELED qilish
        await db.execute("UPDATE sim_orders SET status = 'CANCELED' WHERE id = ?", (order_id,))
        # Mablag'ni qaytarish
        await db.execute("UPDATE users SET balance = balance + ?, spent = spent - ? WHERE telegram_id = ?",
                         (order["price"], order["price"], order["user_id"]))
        await db.commit()
        return dict(order)

# --- STATS VA TO'LOVLAR ---
async def get_user_referrals_count(user_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM users WHERE referrer_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row["count"] if row else 0

async def get_stats():
    async with get_db() as db:
        c1 = await db.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = (await c1.fetchone())["total_users"]

        c2 = await db.execute("SELECT COUNT(*) as total_orders, COALESCE(SUM(price), 0) as total_volume FROM orders")
        r2 = await c2.fetchone()
        smm_orders = r2["total_orders"]
        smm_volume = r2["total_volume"]

        c3 = await db.execute("SELECT COUNT(*) as total_sim_orders, COALESCE(SUM(price), 0) as total_sim_volume FROM sim_orders WHERE status != 'CANCELED'")
        r3 = await c3.fetchone()
        sim_orders = r3["total_sim_orders"]
        sim_volume = r3["total_sim_volume"]

        c4 = await db.execute("SELECT COALESCE(SUM(balance), 0) as total_balance FROM users")
        total_balance = (await c4.fetchone())["total_balance"]

        return {
            "total_users": total_users,
            "total_orders": smm_orders + sim_orders,
            "smm_orders": smm_orders,
            "sim_orders": sim_orders,
            "total_volume": smm_volume + sim_volume,
            "total_balance": total_balance
        }

async def get_all_users():
    async with get_db() as db:
        cursor = await db.execute("SELECT telegram_id FROM users")
        rows = await cursor.fetchall()
        return [r["telegram_id"] for r in rows]

async def create_payment(user_id: int, amount: float, payment_system: str, payment_id: str):
    async with get_db() as db:
        await db.execute("""
        INSERT INTO payments (user_id, amount, payment_system, payment_id, status)
        VALUES (?, ?, ?, ?, 'pending')
        """, (user_id, amount, payment_system, payment_id))
        await db.commit()

async def complete_payment(payment_id: str):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
        payment = await cursor.fetchone()
        if not payment or payment["status"] == "completed":
            return None

        await db.execute("UPDATE payments SET status = 'completed' WHERE payment_id = ?", (payment_id,))
        await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                         (payment["amount"], payment["user_id"]))

        user_cursor = await db.execute("SELECT referrer_id FROM users WHERE telegram_id = ?", (payment["user_id"],))
        user = await user_cursor.fetchone()
        if user and user["referrer_id"] and user["referrer_id"] > 0:
            from config import REFERRAL_BONUS_PERCENT
            bonus = (payment["amount"] * REFERRAL_BONUS_PERCENT) / 100.0
            if bonus > 0:
                await db.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", 
                                 (bonus, user["referrer_id"]))

        await db.commit()
        return dict(payment)

async def update_service_price(service_id: int, new_price: float):
    async with get_db() as db:
        await db.execute("UPDATE services SET price_per_1000 = ? WHERE id = ?", (new_price, service_id))
        await db.commit()
