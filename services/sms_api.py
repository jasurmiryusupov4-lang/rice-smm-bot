import random
import aiohttp
import logging
from config import SMS_API_KEY

logger = logging.getLogger(__name__)

class SMSActivateClient:
    BASE_URL = "https://api.sms-activate.org/stubs/handler_api.php"

    def __init__(self, api_key: str = SMS_API_KEY):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_number(self, service_code: str, country_id: int, prefix: str = "+7") -> dict:
        """
        SMS-Activate orqali yangi raqam olish.
        Agar API kalit kiritilmagan bo'lsa, xatolik chiqarmaydi va demo rejimda raqam shakllantiradi.
        """
        if not self.is_configured():
            # Demo / Test rejimdagi virtual raqam
            mock_id = str(random.randint(10000000, 99999999))
            suffix = "".join([str(random.randint(0, 9)) for _ in range(7)])
            phone = f"{prefix}{suffix}"
            logger.info(f"SMS API sozlanmagan. Demo virtual raqam berildi: {phone}")
            return {
                "ok": True,
                "provider_id": mock_id,
                "phone": phone,
                "is_demo": True
            }

        params = {
            "api_key": self.api_key,
            "action": "getNumber",
            "service": service_code,
            "country": country_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=15) as resp:
                    text = await resp.text()
                    logger.info(f"SMS-Activate javobi: {text}")

                    if text.startswith("ACCESS_NUMBER"):
                        parts = text.split(":")
                        return {
                            "ok": True,
                            "provider_id": parts[1],
                            "phone": f"+{parts[2]}" if not parts[2].startswith("+") else parts[2],
                            "is_demo": False
                        }
                    else:
                        return {"ok": False, "error": text}
        except Exception as e:
            logger.error(f"SMS-Activate API ga ulanishda xatolik: {e}")
            return {"ok": False, "error": str(e)}

    async def get_status(self, provider_id: str) -> dict:
        if not self.is_configured() or not provider_id:
            return {"status": "WAIT_CODE"}

        params = {
            "api_key": self.api_key,
            "action": "getStatus",
            "id": provider_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    text = await resp.text()
                    if text.startswith("STATUS_OK"):
                        code = text.split(":", 1)[1]
                        return {"status": "OK", "code": code}
                    elif text.startswith("STATUS_WAIT_CODE"):
                        return {"status": "WAIT_CODE"}
                    elif text.startswith("STATUS_CANCEL"):
                        return {"status": "CANCEL"}
                    else:
                        return {"status": "OTHER", "raw": text}
        except Exception as e:
            logger.error(f"SMS-Activate Status xatolik: {e}")
            return {"status": "ERROR", "error": str(e)}

    async def set_status(self, provider_id: str, status_code: int) -> bool:
        """
        8 - Bekor qilish (Cancel / Refusal)
        6 - Yakunlash (Complete)
        """
        if not self.is_configured():
            return True

        params = {
            "api_key": self.api_key,
            "action": "setStatus",
            "id": provider_id,
            "status": status_code
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    text = await resp.text()
                    return "ACCESS_CANCEL" in text or "ACCESS_READY" in text or "ACCESS_ACTIVATION" in text
        except Exception as e:
            logger.error(f"SMS-Activate setStatus xatolik: {e}")
            return False

    async def get_balance(self) -> dict:
        if not self.is_configured():
            return {"balance": "0.00", "currency": "RUB (Demo)"}

        params = {
            "api_key": self.api_key,
            "action": "getBalance"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=10) as resp:
                    text = await resp.text()
                    if text.startswith("ACCESS_BALANCE"):
                        balance = text.split(":")[1]
                        return {"balance": balance, "currency": "RUB"}
                    return {"balance": "Xatolik", "raw": text}
        except Exception as e:
            return {"balance": "0.00", "error": str(e)}

sms_client = SMSActivateClient()
