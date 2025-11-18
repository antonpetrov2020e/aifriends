"""
Payment service for YooKassa integration (Phase 3)
Handles Premium subscription payments
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
import httpx
import hmac
import hashlib

from ..database.models import User, Payment


class PaymentService:
    """Service for handling payments through YooKassa"""

    def __init__(self, db_session: Session, shop_id: str, secret_key: str):
        """
        Initialize PaymentService

        Args:
            db_session: SQLAlchemy session
            shop_id: YooKassa shop ID
            secret_key: YooKassa secret key
        """
        self.db = db_session
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_url = "https://api.yookassa.ru/v3"

    async def create_payment(
        self,
        user: User,
        amount: int = 99000,  # 990₽ in kopecks
        description: str = "AI Friends Premium - 1 месяц",
        return_url: Optional[str] = None
    ) -> Optional[Payment]:
        """
        Create payment in YooKassa

        Args:
            user: User who is paying
            amount: Amount in kopecks (default 99000 = 990₽)
            description: Payment description
            return_url: URL to return after payment

        Returns:
            Payment object with confirmation_url
        """
        # Generate idempotence key for YooKassa
        idempotence_key = str(uuid.uuid4())

        # Prepare payment data
        payment_data = {
            "amount": {
                "value": f"{amount / 100:.2f}",  # Convert kopecks to rubles
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://t.me/your_bot"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": user.id,
                "telegram_id": user.telegram_id
            }
        }

        try:
            # Make request to YooKassa
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/payments",
                    json=payment_data,
                    auth=(self.shop_id, self.secret_key),
                    headers={
                        "Idempotence-Key": idempotence_key,
                        "Content-Type": "application/json"
                    }
                )

            if response.status_code != 200:
                print(f"YooKassa error: {response.status_code} - {response.text}")
                return None

            result = response.json()

            # Create Payment record in DB
            payment = Payment(
                user_id=user.id,
                amount=amount,
                currency="RUB",
                status="pending",
                payment_id=result["id"],
                confirmation_url=result["confirmation"]["confirmation_url"],
                subscription_type="premium",
                subscription_period="month",
                expires_at=datetime.utcnow() + timedelta(days=30)
            )

            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)

            return payment

        except Exception as e:
            print(f"Error creating payment: {e}")
            self.db.rollback()
            return None

    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Check payment status in YooKassa

        Args:
            payment_id: YooKassa payment ID

        Returns:
            Payment status: "pending", "succeeded", "canceled"
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/payments/{payment_id}",
                    auth=(self.shop_id, self.secret_key)
                )

            if response.status_code != 200:
                return None

            result = response.json()
            return result.get("status")

        except Exception as e:
            print(f"Error checking payment status: {e}")
            return None

    async def process_webhook(self, webhook_data: Dict) -> bool:
        """
        Process YooKassa webhook notification

        Args:
            webhook_data: Webhook payload from YooKassa

        Returns:
            True if processed successfully
        """
        try:
            event = webhook_data.get("event")
            payment_data = webhook_data.get("object")

            if not payment_data or not event:
                return False

            payment_id = payment_data.get("id")
            status = payment_data.get("status")

            # Find payment in DB
            payment = self.db.query(Payment).filter(
                Payment.payment_id == payment_id
            ).first()

            if not payment:
                print(f"Payment not found: {payment_id}")
                return False

            # Update payment status
            payment.status = status

            if status == "succeeded":
                # Payment successful - activate Premium
                payment.paid_at = datetime.utcnow()

                # Update user Premium status
                user = payment.user
                user.is_premium = True
                user.premium_until = payment.expires_at

                print(f"✅ Premium activated for user {user.telegram_id}")

            elif status == "canceled":
                print(f"❌ Payment canceled: {payment_id}")

            self.db.commit()
            return True

        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.db.rollback()
            return False

    def verify_webhook_signature(
        self,
        webhook_data: str,
        signature: str
    ) -> bool:
        """
        Verify YooKassa webhook signature

        Args:
            webhook_data: Raw webhook body as string
            signature: Signature from HTTP header

        Returns:
            True if signature is valid
        """
        # Calculate expected signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            webhook_data.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def get_user_payment_history(self, user: User) -> list[Payment]:
        """
        Get payment history for user

        Args:
            user: User object

        Returns:
            List of Payment objects
        """
        return self.db.query(Payment).filter(
            Payment.user_id == user.id
        ).order_by(Payment.created_at.desc()).all()

    async def cancel_subscription(self, user: User) -> bool:
        """
        Cancel Premium subscription for user

        Args:
            user: User object

        Returns:
            True if canceled successfully
        """
        try:
            user.is_premium = False
            user.premium_until = None
            self.db.commit()

            print(f"✅ Premium canceled for user {user.telegram_id}")
            return True

        except Exception as e:
            print(f"Error canceling subscription: {e}")
            self.db.rollback()
            return False
