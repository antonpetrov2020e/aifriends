"""
Service for managing user notifications and check-in reminders.
Uses APScheduler for scheduling background tasks.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from telegram import Bot
from telegram.error import TelegramError

from ..database.models import User

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Handles scheduling and sending notifications to users.
    Supports:
    - Daily check-in reminders
    - Contextual memory-based prompts
    - Personalized engagement messages
    """

    # Default check-in messages
    MORNING_MESSAGES = [
        "Доброе утро! ☀️ Как ты сегодня?",
        "Привет! Как начался день?",
        "Доброе утро, {name}! 🌸 Как настроение?",
    ]

    EVENING_MESSAGES = [
        "Привет! Как прошёл день? 🌙",
        "Вечер, {name}! Что хорошего сегодня случилось?",
        "Как ты? Просто хотела узнать 💚",
    ]

    CHECKIN_AFTER_CONVERSATION = [
        "Привет! Помнишь, мы с тобой {days_ago} разговаривали про {topic}? Как там дела?",
        "{name}, как ты? Думала о тебе 💚",
        "Привет! Просто хотела узнать, как ты. Всё хорошо?",
    ]

    def __init__(self, db_session: Session, bot: Bot = None):
        """
        Initialize notification service.

        Args:
            db_session: Database session
            bot: Telegram Bot instance (optional, can be set later)
        """
        self.db = db_session
        self.bot = bot
        self._scheduler = None

    def set_bot(self, bot: Bot):
        """Set the Telegram bot instance."""
        self.bot = bot

    async def send_notification(
        self,
        user: User,
        message: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Send a notification to a user.

        Args:
            user: User object with telegram_id
            message: Message text to send
            parse_mode: Telegram parse mode

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.warning("Bot not initialized, cannot send notification")
            return False

        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"Sent notification to user {user.telegram_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send notification to {user.telegram_id}: {e}")
            return False

    def get_users_for_checkin(self, hours_since_activity: int = 24) -> List[User]:
        """
        Get users who haven't been active for a while and have notifications enabled.

        Args:
            hours_since_activity: Minimum hours since last activity

        Returns:
            List of User objects eligible for check-in
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since_activity)

        users = (
            self.db.query(User)
            .filter(
                User.notifications_enabled == True,
                User.consent_given == True,
                User.updated_at < cutoff
            )
            .all()
        )

        return users

    def format_checkin_message(
        self,
        user: User,
        message_template: str,
        topic: str = None,
        days_ago: int = None
    ) -> str:
        """
        Format a check-in message with user personalization.

        Args:
            user: User object
            message_template: Message template with placeholders
            topic: Topic from previous conversation (optional)
            days_ago: Days since last conversation (optional)

        Returns:
            Formatted message string
        """
        name = user.preferred_name or user.first_name or "друг"

        message = message_template.replace("{name}", name)

        if topic:
            message = message.replace("{topic}", topic)
        if days_ago is not None:
            if days_ago == 1:
                days_text = "вчера"
            elif days_ago < 5:
                days_text = f"{days_ago} дня назад"
            else:
                days_text = f"{days_ago} дней назад"
            message = message.replace("{days_ago}", days_text)

        return message

    async def send_morning_checkin(self, user: User) -> bool:
        """Send morning check-in message."""
        import random
        template = random.choice(self.MORNING_MESSAGES)
        message = self.format_checkin_message(user, template)
        return await self.send_notification(user, message)

    async def send_evening_checkin(self, user: User) -> bool:
        """Send evening check-in message."""
        import random
        template = random.choice(self.EVENING_MESSAGES)
        message = self.format_checkin_message(user, template)
        return await self.send_notification(user, message)

    async def send_contextual_checkin(
        self,
        user: User,
        topic: str,
        days_ago: int
    ) -> bool:
        """
        Send contextual check-in based on previous conversation.

        Args:
            user: User object
            topic: Topic from previous conversation
            days_ago: Days since the conversation
        """
        import random
        template = random.choice(self.CHECKIN_AFTER_CONVERSATION)
        message = self.format_checkin_message(user, template, topic, days_ago)
        return await self.send_notification(user, message)

    def update_user_notification_settings(
        self,
        user: User,
        enabled: bool = None,
        morning_time: str = None,
        evening_time: str = None
    ):
        """
        Update user's notification preferences.

        Args:
            user: User object
            enabled: Enable/disable notifications
            morning_time: Morning check-in time (HH:MM format)
            evening_time: Evening check-in time (HH:MM format)
        """
        if enabled is not None:
            user.notifications_enabled = enabled

        if morning_time is not None:
            user.notification_morning_time = morning_time

        if evening_time is not None:
            user.notification_evening_time = evening_time

        self.db.commit()
        logger.info(f"Updated notification settings for user {user.telegram_id}")

    def get_user_notification_settings(self, user: User) -> dict:
        """
        Get user's current notification settings.

        Returns:
            Dictionary with notification settings
        """
        return {
            "enabled": getattr(user, 'notifications_enabled', False),
            "morning_time": getattr(user, 'notification_morning_time', "09:00"),
            "evening_time": getattr(user, 'notification_evening_time', "21:00"),
        }
