import aiohttp
import logging
from config import SMM_API_URL, SMM_API_KEY

logger = logging.getLogger(__name__)

class SMMClient:
    def __init__(self, api_url: str = SMM_API_URL, api_key: str = SMM_API_KEY):
        self.api_url = api_url.rstrip("/") if api_url else ""
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    async def add_order(self, service_id: int, link: str, quantity: int) -> dict:
        """
        SMM Reseller v2 API orqali yangi buyurtma yuborish.
        Agar API sozlanmagan bo'lsa, xatolik chiqarmaydi, bot ichki rejimda buyurtmani qabul qiladi.
        """
        if not self.is_configured():
            logger.info(f"SMM API sozlanmagan. Ichki buyurtma qabul qilindi: Service={service_id}, Qty={quantity}")
            return {"order": 0, "status": "internal_mode", "note": "SMM API ulanmagan (ichki rejim)"}

        params = {
            "key": self.api_key,
            "action": "add",
            "service": service_id,
            "link": link,
            "quantity": quantity
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=params, timeout=15) as resp:
                    data = await resp.json(content_type=None)
                    logger.info(f"SMM API javobi: {data}")
                    return data
        except Exception as e:
            logger.error(f"SMM API ga ulanishda xatolik: {e}")
            return {"error": str(e)}

    async def get_order_status(self, order_id: int) -> dict:
        if not self.is_configured() or not order_id:
            return {"status": "pending"}

        params = {
            "key": self.api_key,
            "action": "status",
            "order": order_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=params, timeout=10) as resp:
                    return await resp.json(content_type=None)
        except Exception as e:
            logger.error(f"SMM Status tekshirishda xatolik: {e}")
            return {"error": str(e)}

    async def get_balance(self) -> dict:
        if not self.is_configured():
            return {"balance": "0.00", "currency": "USD"}

        params = {
            "key": self.api_key,
            "action": "balance"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=params, timeout=10) as resp:
                    return await resp.json(content_type=None)
        except Exception as e:
            logger.error(f"SMM Balans tekshirishda xatolik: {e}")
            return {"error": str(e)}

smm_client = SMMClient()
