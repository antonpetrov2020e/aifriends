"""
Background job for sending scheduled notifications to users.
"""
import asyncio
import logging
from datetime import datetime, timezone, time
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy.orm import Session

from ..database.models import User, Conversation
from ..services.notification_service import NotificationService
from ..services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class NotificationJob:
    """
    Handles scheduled notification delivery.
    Runs in background to send morning/evening check-ins.
    """

    def __init__(
        self,
        db_session: Session,
        bot: Bot,
        memory_service: MemoryService,
    ):
        self.db = db_session
        self.bot = bot
        self.memory_service = memory_service
        self.notification_service = NotificationService(db_session, bot)

    async def run_check_ins(self):
        """
        Check and send notifications for users who have them enabled.
        Should be called periodically (e.g., every hour).
        """
        now = datetime.now(timezone.utc)
        current_hour = now.hour

        # Get all users with notifications enabled
        users = (
            self.db.query(User)
            .filter(
                User.notifications_enabled == True,
                User.consent_given == True,
            )
            .all()
        )

        logger.info(f"Checking notifications for {len(users)} users")

        for user in users:
            try:
                await self._check_user_notification(user, current_hour)
            except Exception as e:
                logger.error(f"Error sending notification to user {user.telegram_id}: {e}")

    async def _check_user_notification(self, user: User, current_hour: int):
        """
        Check if a user should receive a notification now.

        Args:
            user: User object
            current_hour: Current hour (0-23) in UTC
        """
        # Parse notification times (stored as "HH:MM")
        morning_time = getattr(user, 'notification_morning_time', "09:00")
        evening_time = getattr(user, 'notification_evening_time', "21:00")

        try:
            morning_hour = int(morning_time.split(":")[0])
            evening_hour = int(evening_time.split(":")[0])
        except (ValueError, AttributeError):
            morning_hour = 9
            evening_hour = 21

        # Adjust for Moscow timezone (UTC+3)
        moscow_hour = (current_hour + 3) % 24

        if moscow_hour == morning_hour:
            await self._send_morning_checkin(user)
        elif moscow_hour == evening_hour:
            await self._send_evening_checkin(user)

    async def _send_morning_checkin(self, user: User):
        """Send morning check-in notification."""
        # Get recent topics from memory for contextual message
        topics = self.memory_service.get_recent_topics(user.telegram_id, limit=2)

        if topics:
            topic_text = ", ".join(topics[:2])
            message = f"Доброе утро! ☀️ Как ты сегодня? (Кстати, я помню, что мы говорили про {topic_text})"
        else:
            message = await self._get_random_morning_message(user)

        await self._send_notification(user, message)

    async def _send_evening_checkin(self, user: User):
        """Send evening check-in notification."""
        # Check for recent conversation
        last_conv = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.started_at.desc())
            .first()
        )

        if last_conv and last_conv.ended_at is None:
            # User has an unfinished conversation
            message = "Привет! 🌙 Как ты? Мы не закончили наш разговор..."
        else:
            message = await self._get_random_evening_message(user)

        await self._send_notification(user, message)

    async def _get_random_morning_message(self, user: User) -> str:
        """Get a random personalized morning message."""
        import random
        name = user.preferred_name or user.first_name or "друг"

        messages = [
            f"Доброе утро, {name}! ☀️ Как ты сегодня?",
            "Привет! Как начался день?",
            f"Доброе утро! 🌸 Как настроение, {name}?",
            "Новый день — новые возможности! Как ты?",
        ]
        return random.choice(messages)

    async def _get_random_evening_message(self, user: User) -> str:
        """Get a random personalized evening message."""
        import random
        name = user.preferred_name or user.first_name or "друг"

        messages = [
            f"Привет, {name}! 🌙 Как прошёл день?",
            "Вечер! Что хорошего сегодня случилось?",
            f"Как ты, {name}? Просто хотела узнать 💚",
            "Как дела? Расскажи, что на душе 🌙",
        ]
        return random.choice(messages)

    async def _send_notification(self, user: User, message: str):
        """Send notification and log it."""
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Sent notification to user {user.telegram_id}")
        except TelegramError as e:
            if "bot was blocked" in str(e).lower() or "user is deactivated" in str(e).lower():
                # User blocked the bot or deleted their account
                logger.info(f"User {user.telegram_id} blocked bot, disabling notifications")
                user.notifications_enabled = False
                self.db.commit()
            else:
                logger.error(f"Failed to send notification to {user.telegram_id}: {e}")


async def start_notification_scheduler(
    db_session: Session,
    bot: Bot,
    memory_service: MemoryService,
    interval_seconds: int = 3600,  # Run every hour
):
    """
    Start the notification scheduler as a background task.

    Args:
        db_session: Database session
        bot: Telegram Bot instance
        memory_service: Memory service for context
        interval_seconds: Interval between checks (default: 1 hour)
    """
    job = NotificationJob(db_session, bot, memory_service)

    logger.info(f"Starting notification scheduler (interval: {interval_seconds}s)")

    while True:
        try:
            await job.run_check_ins()
        except Exception as e:
            logger.error(f"Error in notification scheduler: {e}")

        await asyncio.sleep(interval_seconds)
