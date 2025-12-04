"""
Service for handling payments via YooKassa.
"""
import uuid
from yookassa import Configuration, Payment
from src.config import settings

class PaymentService:
    """
    Handles the creation and verification of payments using YooKassa.
    """

    def __init__(self, shop_id: str, secret_key: str):
        """
        Initializes the YooKassa configuration.
        """
        if not shop_id or not secret_key:
            raise ValueError("YooKassa shop_id and secret_key must be provided.")
        
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key

    def create_payment(self, user_id: int, amount: float, currency: str = "RUB", description: str = "") -> Payment | None:
        """
        Creates a new payment in YooKassa.

        Args:
            user_id: The internal ID of the user initiating the payment.
            amount: The payment amount.
            currency: The currency code (e.g., "RUB").
            description: A description for the payment.

        Returns:
            The created Payment object from YooKassa, or None if an error occurred.
        """
        try:
            idempotence_key = str(uuid.uuid4())
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{settings.telegram_bot_token.split(':')[0]}" # A generic return URL
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": user_id
                }
            }, idempotence_key)
            return payment
        except Exception as e:
            import logging
            logging.error(f"Error creating YooKassa payment: {e}")
            return None

    @staticmethod
    def check_payment_status(payment_id: str) -> Payment | None:
        """
        Retrieves the status of a specific payment from YooKassa.

        Args:
            payment_id: The ID of the payment to check.

        Returns:
            The Payment object with updated status, or None if not found.
        """
        try:
            return Payment.find_one(payment_id)
        except Exception as e:
            import logging
            logging.error(f"Error checking YooKassa payment status for {payment_id}: {e}")
            return None

# Global instance, initialized with care
payment_service = None
if settings.yookassa_shop_id and settings.yookassa_secret_key:
    try:
        payment_service = PaymentService(
            shop_id=settings.yookassa_shop_id,
            secret_key=settings.yookassa_secret_key
        )
    except ValueError as e:
        import logging
        logging.warning(f"PaymentService not initialized: {e}")

