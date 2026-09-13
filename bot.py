import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_ID
from database.db import (
    init_db, get_all_waiting_sim_orders, update_sim_order_status, 
    cancel_sim_order_and_refund
)
from handlers.user import user_router
from handlers.order import order_router
from handlers.payment import payment_router
from handlers.admin import admin_router
from handlers.sim import sim_router
from services.sms_api import sms_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def sms_checker_worker(bot: Bot):
    """
    Fondagi avtomatik SMS tekshiruvchi:
    Har 10 soniyada SMS-Activate dan yangi kelgan kodlarni tekshiradi
    va kod kelishi bilan foydalanuvchiga avtomatik yuboradi!
    """
    logger.info("SMS avtomatik tekshiruvchi fonda ishga tushdi...")
    while True:
        try:
            if sms_client.is_configured():
                waiting_orders = await get_all_waiting_sim_orders()
                for order in waiting_orders:
                    status_res = await sms_client.get_status(order["provider_order_id"])
                    st = status_res.get("status")

                    if st == "OK":
                        code = status_res.get("code", "")
                        await update_sim_order_status(order["id"], "RECEIVED", sms_code=code, sms_text=f"Kod: {code}")
                        await sms_client.set_status(order["provider_order_id"], 6)

                        # Foydalanuvchiga avtomatik xabar
                        try:
                            await bot.send_message(
                                chat_id=order["user_id"],
                                text=f"🎉 <b>Yangi SMS kodi keldi!</b>\n\n"
                                     f"📌 <b>Xizmat:</b> {order['service_name']}\n"
                                     f"📞 <b>Raqam:</b> <code>{order['phone_number']}</code>\n"
                                     f"🔑 <b>SMS Kod:</b> <code>{code}</code> <i>(nusxa olish uchun bosing)</i>",
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Foydalanuvchiga SMS yuborishda xato: {e}")

                    elif st == "CANCEL":
                        refunded = await cancel_sim_order_and_refund(order["id"])
                        if refunded:
                            try:
                                await bot.send_message(
                                    chat_id=order["user_id"],
                                    text=f"⚠️ <b>Raqam muddati tugadi yoki bekor qilindi.</b>\n"
                                         f"Raqam: <code>{order['phone_number']}</code>\n"
                                         f"Mablag' ({int(order['price']):,} so'm) balansingizga to'liq qaytarildi.",
                                    parse_mode="HTML"
                                )
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"SMS checker worker xatosi: {e}")

        await asyncio.sleep(10)

async def handle_ping(request):
    return web.Response(text="OK - RICE SMM Bot is running 24/7!")

async def start_web_server():
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health-check veb-serveri {port}-portda ishga tushirildi.")

async def main():
    logger.info("Bot ishga tushirilmoqda...")
    
    # Render va monitoring uchun veb server
    await start_web_server()
    
    # Ma'lumotlar bazasini initsializatsiya qilish
    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    dp.include_router(admin_router)
    dp.include_router(sim_router)
    dp.include_router(order_router)
    dp.include_router(payment_router)
    dp.include_router(user_router)

    # Eski kutilgan xabarlarni o'tkazib yuborish
    await bot.delete_webhook(drop_pending_updates=True)

    bot_user = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_user.username} ({bot_user.full_name})")

    # Fondagi SMS tekshiruvchini ishga tushirish
    asyncio.create_task(sms_checker_worker(bot))

    # Adminga ishga tushganlik haqida bildirishnoma
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="⚡ <b>RICE SMM + FixSIM BOT muvaffaqiyatli ishga tushirildi!</b>\n\n"
                 "🚀 SMM Xizmatlari\n"
                 "📱 Virtual Raqamlar (FixSIM)\n"
                 "💳 To'lovlar va Admin Panel barchasi faol holatda.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Adminga start xabari yuborilmadi: {e}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
