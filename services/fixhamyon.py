import uuid
import logging
from config import FIXHAMYON_API_KEY, FIXHAMYON_MERCHANT_ID

logger = logging.getLogger(__name__)

class FixHamyonService:
    def __init__(self, api_key: str = FIXHAMYON_API_KEY, merchant_id: str = FIXHAMYON_MERCHANT_ID):
        self.api_key = api_key
        self.merchant_id = merchant_id

    def is_configured(self) -> bool:
        return bool(self.merchant_id)

    def create_invoice(self, user_id: int, amount: float) -> dict:
        """
        FixHamyon orqali to'lov havolasini yaratish.
        """
        payment_id = f"PAY_{user_id}_{int(amount)}_{uuid.uuid4().hex[:6]}"
        
        # Agar FixHamyon kassa ID kiritilgan bo'lsa
        if self.merchant_id:
            # Standart FixHamyon bot to'lov havolasi formati
            url = f"https://t.me/FixHamyonBot?start=pay_{self.merchant_id}_{int(amount)}_{payment_id}"
        else:
            url = f"https://t.me/FixHamyonBot"

        return {
            "payment_id": payment_id,
            "url": url,
            "amount": amount
        }

fixhamyon_service = FixHamyonService()
