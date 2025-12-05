"""
Telegram bot handlers for AI Friends bot
Implements Phase 1: Foundation (Onboarding, Panic, Structured Analysis)
Phase 2: Memory & Viral Cards
"""
import asyncio
import logging
import os
import traceback
from typing import List, Dict
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from . import messages as msg
from . import keyboards as kb
from src.config import settings
from ..services.user_service import UserService
from ..services.ai_service import AIService
from ..services.conversation_service import ConversationService
from ..database.models import User, Conversation, Message

logger = logging.getLogger(__name__)


class BotHandlers:
    """Main bot handlers class"""

    # Rate limiting constants
    MAX_MESSAGES_PER_HOUR = settings.max_messages_per_hour
    MAX_CARDS_PER_HOUR = settings.max_cards_per_hour
    MAX_TEXT_LENGTH = 4000  # Maximum characters for user input

    def __init__(
        self,
        db_session: Session,
        ai_service: AIService,
        memory_service,
        card_service,
        payment_service,
        free_analysis_limit: int = 3
    ):
        self.db = db_session
        self.user_service = UserService(db_session)
        self.conversation_service = ConversationService(db_session)
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.card_service = card_service
        self.payment_service = payment_service
        self.free_analysis_limit = free_analysis_limit

    def _check_rate_limit(self, context: ContextTypes.DEFAULT_TYPE, limit_type: str = "messages") -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit.

        Args:
            context: Telegram context with user_data
            limit_type: Type of limit to check ("messages" or "cards")

        Returns:
            Tuple of (is_allowed, remaining_count)
        """
        from datetime import datetime, timedelta

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)

        if limit_type == "messages":
            timestamps_key = "message_timestamps"
            max_limit = self.MAX_MESSAGES_PER_HOUR
        else:  # cards
            timestamps_key = "card_timestamps"
            max_limit = self.MAX_CARDS_PER_HOUR

        # Get existing timestamps
        timestamps = context.user_data.get(timestamps_key, [])

        # Filter to only last hour
        timestamps = [ts for ts in timestamps if ts > hour_ago]

        # Update stored timestamps
        context.user_data[timestamps_key] = timestamps

        remaining = max_limit - len(timestamps)
        is_allowed = remaining > 0

        return is_allowed, remaining

    def _record_rate_limit_usage(self, context: ContextTypes.DEFAULT_TYPE, limit_type: str = "messages"):
        """Record a usage event for rate limiting."""
        from datetime import datetime

        now = datetime.now(timezone.utc)

        if limit_type == "messages":
            timestamps_key = "message_timestamps"
        else:  # cards
            timestamps_key = "card_timestamps"

        timestamps = context.user_data.get(timestamps_key, [])
        timestamps.append(now)
        context.user_data[timestamps_key] = timestamps

    def _validate_user_input(self, text: str) -> tuple[bool, str]:
        """
        Validate user input text.

        Args:
            text: User's input text

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Сообщение не может быть пустым."

        if len(text) > self.MAX_TEXT_LENGTH:
            return False, f"Сообщение слишком длинное. Максимум {self.MAX_TEXT_LENGTH} символов."

        return True, ""

    def _cleanup_user_context(self, context: ContextTypes.DEFAULT_TYPE, keys_to_keep: list = None):
        """
        Clean up user context data to prevent memory leaks.

        Args:
            context: Telegram context
            keys_to_keep: List of keys to preserve (optional)
        """
        if keys_to_keep is None:
            keys_to_keep = []

        # Keys that should persist across conversations
        persistent_keys = [
            "message_timestamps",
            "card_timestamps",
        ]
        persistent_keys.extend(keys_to_keep)

        # Clean up non-persistent keys
        keys_to_remove = [
            key for key in list(context.user_data.keys())
            if key not in persistent_keys
        ]

        for key in keys_to_remove:
            context.user_data.pop(key, None)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - Improved onboarding flow"""
        telegram_user = update.effective_user

        # Get or create user
        user = self.user_service.get_or_create_user(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )

        # If user already completed onboarding, show personalized welcome
        if user.onboarding_completed:
            display_name = self.user_service.get_display_name(user)

            # Get last conversation for context
            last_conv = (
                self.db.query(Conversation)
                .filter(Conversation.user_id == user.id)
                .order_by(Conversation.started_at.desc())
                .first()
            )

            if last_conv:
                # Handle naive datetime from DB
                started_at = last_conv.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                days_ago = (datetime.now(timezone.utc) - started_at).days

                if days_ago == 0:
                    greeting = f"С возвращением, {display_name}! 👋\n\nПродолжим?"
                elif days_ago < 7:
                    greeting = f"Привет, {display_name}! Прошло {days_ago} дней. Как дела?"
                else:
                    greeting = f"Рада видеть, {display_name}! Давно не виделись ({days_ago} дней). Что нового?"
            else:
                greeting = f"С возвращением, {display_name}! 👋\n\nЧем могу помочь?"

            await update.message.reply_text(
                greeting,
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        # NEW ONBOARDING FLOW
        # Step 1: Welcome
        await update.message.reply_text(msg.WELCOME_MESSAGE, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)

        # Step 2: Ask for name
        await update.message.reply_text(msg.ASK_NAME, parse_mode=ParseMode.HTML)
        context.user_data["waiting_for"] = "name"

    async def onboarding_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle onboarding flow callbacks"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)
        display_name = self.user_service.get_display_name(user)

        if query.data == "show_features":
            # Show quick feature intro
            await query.edit_message_text(
                msg.FEATURES_QUICK_INTRO,
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(2)

            # Then show consent
            await query.message.reply_text(
                msg.CONSENT_ACCEPTED,
                reply_markup=kb.get_consent_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "skip_to_panic":
            # User needs urgent help - skip to panic mode
            self.user_service.give_consent(user)  # Implicit consent
            self.user_service.complete_onboarding(user)

            await query.edit_message_text(
                f"Хорошо, {display_name}, я здесь 💚\n\nСейчас поможем.",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(1)

            # Start panic flow
            await query.message.reply_text(msg.PANIC_GREETING, parse_mode=ParseMode.HTML)
            await asyncio.sleep(2)
            await query.message.reply_text(msg.PANIC_BREATHING, parse_mode=ParseMode.HTML)
            await asyncio.sleep(3)
            await query.message.reply_text(
                msg.PANIC_CHECK_IN,
                reply_markup=kb.get_panic_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "skip_onboarding":
            # Skip to main menu
            self.user_service.give_consent(user)  # Implicit consent
            self.user_service.complete_onboarding(user)

            await query.edit_message_text(
                f"Отлично, {display_name}! 👌\n\nЧем могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "first_need_analysis":
            # User wants to analyze situation
            await query.edit_message_text(
                "Окей, давай разбираться 🔍",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(1)
            await query.message.reply_text(
                msg.ANALYSIS_INTRO,
                reply_markup=kb.get_analysis_situation_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "first_need_panic":
            # User is anxious
            await query.edit_message_text(
                "Понимаю. Давай поможем тебе успокоиться.",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(1)
            await query.message.reply_text(msg.PANIC_GREETING, parse_mode=ParseMode.HTML)
            await asyncio.sleep(2)
            await query.message.reply_text(msg.PANIC_BREATHING, parse_mode=ParseMode.HTML)
            await asyncio.sleep(3)
            await query.message.reply_text(
                msg.PANIC_CHECK_IN,
                reply_markup=kb.get_panic_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "first_need_journal":
            # User wants to journal
            await query.edit_message_text(
                "Отлично! Это твое личное пространство 🌿",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(1)
            await query.message.reply_text(
                msg.JOURNAL_INTRO,
                parse_mode=ParseMode.HTML,
            )
            context.user_data["conversation_mode"] = "journal"
            context.user_data["conversation_history"] = []

        elif query.data == "first_need_explore":
            # User is just exploring
            await query.edit_message_text(
                f"Без проблем, {display_name}! Осматривайся 😊\n\nКогда будешь готова — вот меню:",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def consent_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle consent button callback"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)
        display_name = self.user_service.get_display_name(user)

        if query.data == "consent_yes":
            # Give consent
            self.user_service.give_consent(user)
            self.user_service.complete_onboarding(user)

            # Show personalized completion message with first question
            await query.edit_message_text(
                msg.ONBOARDING_COMPLETE.format(name=display_name),
                reply_markup=kb.get_first_need_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "privacy_policy":
            # Show privacy policy (placeholder for now)
            privacy_text = """**Политика конфиденциальности**

🔒 Мы храним:
- Ваш Telegram ID (чтобы узнавать вас)
- Историю наших разговоров (чтобы помнить контекст)

🔒 Мы НЕ храним:
- Ваш номер телефона
- Контакты
- Медиафайлы (фото, видео)

🔒 Ваши права:
- Удалить всю историю в любой момент
- Отозвать согласие
- Экспортировать данные

Все данные хранятся на серверах в РФ (ФЗ-152).

[Полная версия: ссылка]"""

            await query.edit_message_text(privacy_text, reply_markup=kb.get_consent_keyboard(),
                parse_mode="Markdown",
            )

    async def navigation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle navigation callbacks (back_to_analysis, continue_talk, etc.)"""
        query = update.callback_query
        await query.answer()

        if query.data == "back_to_analysis":
            # User wants to go back to situation selection
            await query.edit_message_text(
                "Хорошо, давай выберем заново.\n\nЧто случилось?",
                reply_markup=kb.get_analysis_situation_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "continue_talk":
            # User wants to continue conversation
            await query.edit_message_text(
                "Я слушаю 👂\n\nПиши всё, что хочешь.",
                parse_mode=ParseMode.HTML,
            )
            # Keep current conversation mode active
            # (it's already set in context.user_data)

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "back_to_menu":
            # Clean up user context to prevent memory leaks
            self._cleanup_user_context(context)

            await query.edit_message_text(
                "Чем могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def panic_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Panic button - immediate anxiety relief"""
        query = update.callback_query
        await query.answer()

        # Phase 1: Static calming response
        await query.edit_message_text(msg.PANIC_GREETING, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)

        await query.message.reply_text(msg.PANIC_BREATHING, parse_mode=ParseMode.HTML)
        await asyncio.sleep(6)

        await query.message.reply_text(msg.PANIC_CHECK_IN, reply_markup=kb.get_panic_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def panic_response_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panic follow-up responses"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        if query.data == "panic_better":
            response = """Вот и отлично! 💚

Помни: паника — это не опасно. Это просто сигнал от твоего тела.

Ты справилась. Горжусь тобой 💪"""

            await query.edit_message_text(response, reply_markup=kb.get_continue_or_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

        elif query.data == "panic_continue":
            # Offer alternative calming technique on repeat
            panic_count = context.user_data.get("panic_repeat_count", 0)
            context.user_data["panic_repeat_count"] = panic_count + 1

            if panic_count == 0:
                # Second time - try alternative breathing
                await query.edit_message_text(
                    "Давай попробуем другую технику 💙",
                    parse_mode=ParseMode.HTML,
                )
                await asyncio.sleep(1)
                await query.message.reply_text(msg.PANIC_BREATHING_ALT, parse_mode=ParseMode.HTML)
            else:
                # Third+ time - try grounding technique
                await query.edit_message_text(
                    "Хорошо, давай попробуем что-то другое 🌿",
                    parse_mode=ParseMode.HTML,
                )
                await asyncio.sleep(1)
                await query.message.reply_text(msg.PANIC_GROUNDING, parse_mode=ParseMode.HTML)

            await asyncio.sleep(8)
            await query.message.reply_text(
                msg.PANIC_CHECK_IN,
                reply_markup=kb.get_panic_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        elif query.data == "panic_talk":
            # Switch to free-form conversation mode
            await query.edit_message_text(
                "Я слушаю тебя 👂\n\nПиши всё, что хочешь. Без фильтров.",
                parse_mode=ParseMode.HTML,
            )
            # Set context for conversation tracking
            context.user_data["conversation_mode"] = "panic_talk"

            # Get or create conversation in DB
            conversation = self.conversation_service.get_or_create_conversation(
                user=user,
                conversation_type="panic"
            )
            context.user_data["conversation_id"] = conversation.id

    async def analysis_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start 'Analysis' flow - check limits first"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Check if user can start analysis
        can_analyze, remaining = self.user_service.check_analysis_limit(
            user, self.free_analysis_limit
        )

        if not can_analyze:
            # Show freemium limit message
            limit_msg = msg.FREE_LIMIT_REACHED.format(
                limit=self.free_analysis_limit,
                price=settings.premium_price_monthly,
            )
            await query.edit_message_text(limit_msg, reply_markup=kb.get_back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
            return

        # Increment counter
        self.user_service.increment_analysis_count(user)

        # Show remaining count for free users
        remaining_text = ""
        if not user.is_premium and remaining > 0:
            remaining_text = f"\n\n_Осталось бесплатных разборов на неделю: {remaining - 1}_"

        # Start analysis flow
        await query.edit_message_text(msg.ANALYSIS_INTRO + remaining_text, reply_markup=kb.get_analysis_situation_keyboard(),
            parse_mode="Markdown",
        )

    async def situation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle situation selection"""
        query = update.callback_query
        await query.answer()

        # Store selected situation in context
        situation = query.data.replace("situation_", "")
        context.user_data["current_situation"] = situation

        # Route to appropriate response based on situation
        if situation == "no_message":
            response = msg.ANALYSIS_SITUATION_HE_DOESNT_WRITE
        elif situation == "fight":
            response = msg.ANALYSIS_SITUATION_FIGHT
        elif situation == "strange":
            response = msg.ANALYSIS_SITUATION_STRANGE_MESSAGE
        else:  # other
            response = "Расскажи, что случилось? Можешь в свободной форме."

        await query.edit_message_text(response, parse_mode=ParseMode.HTML)

        # Set conversation mode to capture text input
        context.user_data["conversation_mode"] = "situation_description"
        context.user_data["waiting_for"] = "situation_details"

    async def _handle_onboarding_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's name during onboarding."""
        text = update.message.text
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Save preferred name
        self.user_service.set_preferred_name(user, text.strip())

        # Send personalized greeting
        await update.message.reply_text(
            msg.NICE_TO_MEET.format(name=text.strip()),
            reply_markup=kb.get_show_features_keyboard(),
            parse_mode=ParseMode.HTML,
        )

        # Clear waiting state
        context.user_data["waiting_for"] = None

    async def _handle_situation_details_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's situation details input."""
        text = update.message.text
        context.user_data["current_situation"] = text

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Get user's name for personalization
        display_name = self.user_service.get_display_name(user)

        # Create or get conversation for analysis
        conversation = self.conversation_service.get_or_create_conversation(
            user=user,
            conversation_type="analysis"
        )
        context.user_data["conversation_id"] = conversation.id

        # Set conversation mode for follow-up messages
        context.user_data["conversation_mode"] = "analysis_dialogue"
        context.user_data["conversation_history"] = []

        # Save situation description to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=text,
            message_type="situation_description"
        )

        try:
            # Generate empathetic response with active listening
            empathetic_response = await self.ai_service.empathetic_first_response(
                user_story=text,
                user_name=display_name
            )

            # Save empathetic response to DB
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=empathetic_response
            )

            # Save to conversation history for context
            context.user_data["conversation_history"].append({"role": "user", "content": text})
            context.user_data["conversation_history"].append({"role": "assistant", "content": empathetic_response})

            # Send empathetic response WITHOUT buttons - let the user respond naturally
            await update.message.reply_text(
                empathetic_response,
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:
            logger.error(f"Error in empathetic first response: {e}", exc_info=True)
            # Fallback to direct question
            fallback_msg = f"{display_name}, я вижу, что это для тебя важно. Расскажи подробнее — что ты почувствовала в тот момент?"

            # Save fallback to DB
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=fallback_msg
            )

            await update.message.reply_text(
                fallback_msg,
                parse_mode=ParseMode.HTML,
            )

        # Clear waiting state
        context.user_data["waiting_for"] = None

    async def _handle_panic_talk_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages in panic_talk mode."""
        text = update.message.text
        conversation_history = context.user_data.get("conversation_history", [])
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Get conversation from DB
        conversation_id = context.user_data.get("conversation_id")
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        else:
            # Fallback: create conversation if not exists
            conversation = self.conversation_service.get_or_create_conversation(
                user=user,
                conversation_type="panic"
            )
            context.user_data["conversation_id"] = conversation.id

        # Load conversation history from DB
        conversation_history = self.conversation_service.get_conversation_history(
            conversation=conversation,
            limit=20  # Last 20 messages for context
        )

        # Save user message to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=text
        )

        try:
            # Recall relevant memories (Phase 2)
            memories = self.memory_service.search_memories(
                user_id=telegram_user.id,
                query_text=text,
                n_results=3,
            )
            memory_context = ""
            if memories:
                formatted_memories = "\n- ".join(memories)
                memory_context = f"Вот некоторые выдержки из наших прошлых разговоров:\n- {formatted_memories}"


            # Get AI response
            response = await self.ai_service.chat(
                user_message=text,
                conversation_history=conversation_history[:-1],  # Exclude current message
                context=f"Пользователь в режиме 'паника' - нужна эмоциональная поддержка, валидация чувств и короткий эмпатичный ответ (2-3 предложения). Не давай советов, просто поддержи.\n\n{memory_context}"
            )

            # Save the turn to memory
            self.memory_service.add_memory(
                user_id=telegram_user.id,
                text=f"User: {text}\nAssistant: {response}",
                metadata={"mode": "panic_talk"}
            )

            # Save AI response to DB
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=response
            )

            await update.message.reply_text(response, parse_mode=ParseMode.HTML)

            # Check for insight (don't block on error)
            try:
                has_insight = await self.ai_service.detect_insight(text)
                if has_insight:
                    # Save insight text for card generation (Phase 2)
                    context.user_data["last_insight_text"] = text
                    await asyncio.sleep(1)

                    if self.user_service.is_premium(user):
                        prompt = msg.INSIGHT_DETECTED + "\n\n" + "Выбери стиль для своей карточки:"
                        keyboard = kb.get_premium_card_keyboard()
                    else:
                        prompt = msg.INSIGHT_DETECTED + "\n\n" + msg.INSIGHT_SHARE_OFFER
                        keyboard = kb.get_insight_share_keyboard()

                    await update.message.reply_text(
                        prompt,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML,
                    )
            except Exception:
                pass  # Silently ignore insight detection errors
        except Exception as e:
            logger.error(f"Error in panic_talk mode: {e}", exc_info=True)
            # Show empathetic error message
            await update.message.reply_text(
                "Слушай, у меня что-то тормозит сейчас 😔\n\nНо я здесь и слышу тебя. Продолжай, если хочешь, или можем вернуться к главному меню.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def _handle_analysis_dialogue_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages in analysis_dialogue mode - free-form conversation about the situation."""
        text = update.message.text
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)
        display_name = self.user_service.get_display_name(user)

        # Get conversation from DB
        conversation_id = context.user_data.get("conversation_id")
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        else:
            conversation = self.conversation_service.get_or_create_conversation(
                user=user,
                conversation_type="analysis"
            )
            context.user_data["conversation_id"] = conversation.id

        # Get conversation history from context
        conversation_history = context.user_data.get("conversation_history", [])

        # Save user message to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=text
        )

        # Add to history
        conversation_history.append({"role": "user", "content": text})

        try:
            # Continue empathetic dialogue
            ai_response = await self.ai_service.chat(
                user_message=text,
                conversation_history=conversation_history,
                context=f"Это продолжение разговора с {display_name} о её ситуации. Продолжай активное слушание, задавай открытые вопросы, помогай разобраться в чувствах. Обращайся по имени иногда."
            )

            # Save AI response
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=ai_response
            )

            # Update history
            conversation_history.append({"role": "assistant", "content": ai_response})
            context.user_data["conversation_history"] = conversation_history

            await update.message.reply_text(
                ai_response,
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:
            logger.error(f"Error in analysis_dialogue: {e}", exc_info=True)
            await update.message.reply_text(
                f"{display_name}, прости, что-то пошло не так. Можешь повторить?",
                parse_mode=ParseMode.HTML,
            )

    async def _handle_thinking_dialogue_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages in thinking_dialogue mode."""
        text = update.message.text
        conversation_history = context.user_data.get("conversation_history", [])
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Get conversation from DB
        conversation_id = context.user_data.get("conversation_id")
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        else:
            # Fallback: create conversation if not exists
            conversation = self.conversation_service.get_or_create_conversation(
                user=user,
                conversation_type="analysis"
            )
            context.user_data["conversation_id"] = conversation.id

        # Load conversation history from DB
        conversation_history = self.conversation_service.get_conversation_history(
            conversation=conversation,
            limit=20  # Last 20 messages for context
        )

        # Save user message to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=text
        )

        try:
            # Recall relevant memories (Phase 2)
            memories = self.memory_service.search_memories(
                user_id=telegram_user.id,
                query_text=text,
                n_results=3,
            )
            memory_context = ""
            if memories:
                formatted_memories = "\n- ".join(memories)
                memory_context = f"Вот некоторые выдержки из наших прошлых разговоров:\n- {formatted_memories}"

            # Get AI response with Socratic method
            response = await self.ai_service.chat(
                user_message=text,
                conversation_history=conversation_history[:-1],  # Exclude current message
                context=f"Продолжай задавать короткие наводящие вопросы (1-2 предложения). Помоги пользователю самостоятельно прийти к решению. Не давай прямых советов.\n\n{memory_context}"
            )

            # Save the turn to memory
            self.memory_service.add_memory(
                user_id=telegram_user.id,
                text=f"User: {text}\nAssistant: {response}",
                metadata={"mode": "thinking_dialogue"}
            )

            # Save AI response to DB
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=response
            )

            await update.message.reply_text(response, parse_mode=ParseMode.HTML)

            # Check for insight (don't block on error)
            try:
                has_insight = await self.ai_service.detect_insight(text)
                if has_insight:
                    # Save insight text for card generation (Phase 2)
                    context.user_data["last_insight_text"] = text
                    await asyncio.sleep(1)
                    
                    if self.user_service.is_premium(user):
                        prompt = msg.INSIGHT_DETECTED + "\n\n" + "Выбери стиль для своей карточки:"
                        keyboard = kb.get_premium_card_keyboard()
                    else:
                        prompt = msg.INSIGHT_DETECTED + "\n\n" + msg.INSIGHT_SHARE_OFFER
                        keyboard = kb.get_insight_share_keyboard()

                    await update.message.reply_text(
                        prompt,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML,
                    )
            except Exception:
                pass  # Silently ignore insight detection errors
        except Exception as e:
            logger.error(f"Error in thinking_dialogue mode: {e}", exc_info=True)
            # Show empathetic error message
            await update.message.reply_text(
                "Упс, что-то пошло не так 😔\n\nДавай попробуем ещё раз, или можем вернуться к главному меню.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def _handle_adding_win_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages in adding_win mode."""
        text = update.message.text
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)
        
        self.user_service.add_win(user, text)
        
        await update.message.reply_text(
            "Отлично, победа записана! 💪",
            reply_markup=kb.get_wins_keyboard()
        )
        context.user_data.pop("conversation_mode", None)

    async def _handle_general_conversation_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general conversation messages."""
        text = update.message.text
        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Try to get most recent active conversation
        conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user.id,
                Conversation.ended_at.is_(None)
            )
            .order_by(Conversation.started_at.desc())
            .first()
        )

        if not conversation:
            # Create new general conversation
            conversation = self.conversation_service.get_or_create_conversation(
                user=user,
                conversation_type="general"
            )
            context.user_data["conversation_id"] = conversation.id
            context.user_data["conversation_mode"] = "general"

        # Load full conversation history from DB
        conversation_history = self.conversation_service.get_conversation_history(
            conversation=conversation,
            limit=30  # Last 30 messages for context
        )

        # Save user message to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=text
        )

        try:
            # Recall relevant memories
            memories = self.memory_service.search_memories(
                user_id=telegram_user.id,
                query_text=text,
                n_results=5,
            )
            memory_context = ""
            if memories:
                formatted_memories = "\n- ".join(memories)
                memory_context = f"Вот некоторые выдержки из наших прошлых разговоров:\n- {formatted_memories}"

            # Get summary of recent topics for better context
            recent_summary = self.conversation_service.get_recent_conversations_summary(
                user=user,
                days=7,
                limit=3
            )

            context_prompt = "Свободное общение. Используй АКТИВНОЕ СЛУШАНИЕ."
            if recent_summary:
                context_prompt += f"\n\nКраткая история последних разговоров:\n{recent_summary}"
            if memory_context:
                context_prompt += f"\n\n{memory_context}"


            # Get AI response with full history
            response = await self.ai_service.chat(
                user_message=text,
                conversation_history=conversation_history,
                context=context_prompt
            )

            # Save the turn to memory
            self.memory_service.add_memory(
                user_id=telegram_user.id,
                text=f"User: {text}\nAssistant: {response}",
                metadata={"mode": "general"}
            )

            # Save AI response to DB
            self.conversation_service.save_message(
                conversation=conversation,
                role="assistant",
                content=response
            )

            await update.message.reply_text(response, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Error in general conversation: {e}", exc_info=True)
            await update.message.reply_text(
                "Не совсем поняла 🤔\n\nВыбери, пожалуйста, что тебе нужно:",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle free-form text messages based on conversation context"""
        text = update.message.text
        conversation_mode = context.user_data.get("conversation_mode")
        waiting_for = context.user_data.get("waiting_for")

        # Validate user input
        is_valid, error_msg = self._validate_user_input(text)
        if not is_valid:
            await update.message.reply_text(
                error_msg,
                parse_mode=ParseMode.HTML,
            )
            return

        # Check rate limit (except for name input which is part of onboarding)
        if waiting_for != "name":
            is_allowed, remaining = self._check_rate_limit(context, "messages")
            if not is_allowed:
                await update.message.reply_text(
                    "Ты отправила слишком много сообщений за последний час. "
                    "Давай сделаем небольшую паузу? Попробуй снова чуть позже 💙",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Record usage
            self._record_rate_limit_usage(context, "messages")

        if waiting_for == "name":
            await self._handle_onboarding_name_input(update, context)
            return

        elif waiting_for == "situation_details":
            await self._handle_situation_details_input(update, context)
            return

        elif conversation_mode == "panic_talk":
            await self._handle_panic_talk_message(update, context)
            return

        elif conversation_mode == "thinking_dialogue":
            await self._handle_thinking_dialogue_message(update, context)
            return

        elif conversation_mode == "adding_win":
            await self._handle_adding_win_message(update, context)
            return

        elif conversation_mode == "analysis_dialogue":
            await self._handle_analysis_dialogue_message(update, context)
            return

        else:
            await self._handle_general_conversation_message(update, context)
            return

    async def feeling_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feeling selection and provide validation"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        feeling = query.data.replace("feeling_", "")
        context.user_data["current_feeling"] = feeling

        # Get situation context
        situation = context.user_data.get("current_situation", "")

        # Use predefined empathetic messages (more reliable than AI for this)
        feeling_messages = {
            "anger": msg.FEELING_ANGER,
            "hurt": msg.FEELING_HURT,
            "anxiety": msg.FEELING_ANXIETY,
            "confusion": msg.FEELING_CONFUSION,
            "unknown": msg.FEELING_UNKNOWN,
        }

        response = feeling_messages.get(feeling, msg.FEELING_CONFUSION)

        await query.edit_message_text(response, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)

        # Create conversation in DB for analysis
        conversation = self.conversation_service.get_or_create_conversation(
            user=user,
            conversation_type="analysis"
        )
        context.user_data["conversation_id"] = conversation.id

        # Start Socratic questioning with AI
        feeling_names = {
            "anger": "злость",
            "hurt": "обиду",
            "anxiety": "тревогу",
            "confusion": "растерянность",
            "unknown": "смешанные чувства, которые сложно определить",
        }
        feeling_name = feeling_names.get(feeling, feeling)

        # Save initial context to conversation
        initial_context = f"Ситуация: {situation}\nЯ чувствую: {feeling_name}"
        self.conversation_service.save_message(
            conversation=conversation,
            role="user",
            content=initial_context,
            message_type="context"
        )

        first_question = await self.ai_service.chat(
            user_message=initial_context,
            conversation_history=[],
            context=f"Пользователь описал ситуацию и чувство '{feeling_name}'. СНАЧАЛА коротко отрази/валидируй это чувство (1 предложение), ПОТОМ задай ОДИН наводящий вопрос (метод Сократа) чтобы помочь разобраться в настоящих желаниях, страхах или границах. Всего 2-3 предложения."
        )

        # Save first question to DB
        self.conversation_service.save_message(
            conversation=conversation,
            role="assistant",
            content=first_question
        )

        await query.message.reply_text(first_question, parse_mode=ParseMode.HTML)

        # Set conversation mode for thinking dialogue
        context.user_data["conversation_mode"] = "thinking_dialogue"

    async def journal_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start journal mode"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Show journal intro
        await query.edit_message_text(
            msg.JOURNAL_INTRO,
            parse_mode=ParseMode.HTML,
        )

        # Set conversation mode for journal
        context.user_data["conversation_mode"] = "journal"
        context.user_data["conversation_history"] = []
        context.user_data["journal_entry_count"] = 0

    async def journal_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle journal-related callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "journal_continue":
            # User wants to continue writing
            await query.edit_message_text(
                msg.JOURNAL_PROMPT_GENERAL,
                parse_mode=ParseMode.HTML,
            )
            # Keep conversation mode active
            context.user_data["conversation_mode"] = "journal"

    async def wins_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Diary of Wins feature callbacks"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # This is a premium feature
        if not self.user_service.is_premium(user):
            await query.edit_message_text(
                "🏆 **Дневник побед** — это премиум-функция.\n\nОна позволяет сохранять и пересматривать свои достижения, чтобы укреплять уверенность в себе.\n\nХочешь попробовать?",
                reply_markup=kb.get_settings_keyboard(), # Redirect to settings to see premium
                parse_mode="Markdown"
            )
            return
        
        if query.data == "diary_of_wins":
            wins = self.user_service.get_wins(user)
            if not wins:
                message = "Твой Дневник побед пока пуст. Давай это исправим! ✨\n\nРасскажи о своей маленькой или большой победе сегодня."
            else:
                message = "Твои последние победы:\n\n"
                for win in wins[:5]: # Show last 5
                    message += f"• _{win.content}_ ({win.created_at.strftime('%d.%m.%Y')})\n"
                message += "\nГоржусь тобой! 💪"

            await query.edit_message_text(
                message,
                reply_markup=kb.get_wins_keyboard(),
                parse_mode="Markdown"
            )
        
        elif query.data == "add_win":
            await query.edit_message_text(
                "Какая у тебя сегодня победа? Это может быть что угодно, от 'вышла на пробежку' до 'закрыла большой проект'.\n\nНапиши ее 👇",
                parse_mode=ParseMode.HTML
            )
            context.user_data["conversation_mode"] = "adding_win"

    async def settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings menu"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        if query.data == "settings":
            await query.edit_message_text("⚙️ **Настройки**", reply_markup=kb.get_settings_keyboard(),
                parse_mode="Markdown",
            )

        elif query.data == "delete_history":
            # Show confirmation dialog
            confirm_text = """⚠️ **Удаление истории**

Ты уверена? Это действие нельзя отменить.

Будут удалены:
- Вся история разговоров
- Все воспоминания
- Все созданные карточки

Твой аккаунт останется, но мы начнем с чистого листа."""

            await query.edit_message_text(confirm_text, reply_markup=kb.get_delete_confirm_keyboard(),
                parse_mode="Markdown",
            )

        elif query.data == "confirm_delete":
            # Actually delete the history
            success = self.user_service.delete_user_data(user)

            if success:
                # Clear context
                context.user_data.clear()

                await query.edit_message_text(
                    "✅ История успешно удалена.\n\nМы начинаем с чистого листа 🌱",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
            else:
                await query.edit_message_text(
                    "❌ Что-то пошло не так. Попробуй позже или напиши в поддержку.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )

        elif query.data == "notifications":
            # Notifications settings (placeholder for Phase 2)
            await query.answer("Настройка уведомлений появится в следующей версии!", show_alert=True)

        elif query.data == "premium":
            # Show premium subscription info
            price = settings.premium_price_monthly

            premium_text = f"""👑 **Premium подписка**

**Стоимость:** {price}₽ / месяц

**Что входит:**
✅ Безлимитные "Разборы полётов" (вместо 3 в неделю)
✅ Расширенная память обо всех наших разговорах
✅ Дневник побед — записывай свои достижения
✅ Премиум-шаблоны для карточек инсайтов
✅ Приоритетная поддержка

**Как это работает:**
После оплаты Premium активируется мгновенно. Ты сможешь пользоваться всеми функциями без ограничений целый месяц."""

            # Check if payment service is configured
            if self.payment_service:
                payment = self.payment_service.create_payment(
                    user_id=user.id,
                    amount=float(price),
                    description="Premium-подписка на 1 месяц",
                )

                if payment and payment.confirmation and payment.confirmation.confirmation_url:
                    context.user_data["pending_payment_id"] = payment.id
                    keyboard = [
                        [InlineKeyboardButton(f"💳 Оплатить {price}₽", url=payment.confirmation.confirmation_url)],
                        [InlineKeyboardButton("✅ Я оплатила", callback_data="check_payment")],
                        [InlineKeyboardButton("« Назад", callback_data="settings")],
                    ]
                else:
                    keyboard = [
                        [InlineKeyboardButton(f"💳 Оплатить {price}₽", callback_data="payment_demo")],
                        [InlineKeyboardButton("« Назад", callback_data="settings")],
                    ]
            else:
                # Demo mode - show interface without real payment
                keyboard = [
                    [InlineKeyboardButton(f"💳 Оплатить {price}₽", callback_data="payment_demo")],
                    [InlineKeyboardButton("« Назад", callback_data="settings")],
                ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(premium_text, reply_markup=reply_markup, parse_mode="Markdown")

        elif query.data == "payment_demo":
            # Demo payment screen (for YooKassa screenshots)
            price = settings.premium_price_monthly
            demo_text = f"""💳 **Оформление заказа**

**Товар:** Premium подписка (1 месяц)
**Сумма:** {price}₽

━━━━━━━━━━━━━━━━━━━━

🔒 Безопасная оплата через ЮKassa

Доступные способы оплаты:
• Банковская карта (Visa, MasterCard, МИР)
• СБП (Система быстрых платежей)
• ЮMoney
• SberPay

После оплаты Premium активируется автоматически."""

            keyboard = [
                [InlineKeyboardButton("💳 Перейти к оплате", callback_data="payment_processing")],
                [InlineKeyboardButton("« Назад", callback_data="premium")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(demo_text, reply_markup=reply_markup, parse_mode="Markdown")

        elif query.data == "payment_processing":
            # Demo: payment in progress
            await query.answer("⏳ Подключение платёжной системы в процессе. Скоро будет доступно!", show_alert=True)

    async def check_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 'check_payment' button after user initiates payment"""
        query = update.callback_query
        await query.answer("Проверяю статус оплаты...")

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)
        
        payment_id = context.user_data.get("pending_payment_id")

        if not payment_id:
            await query.edit_message_text(
                "Не нашла активных платежей для проверки. Попробуй начать заново из меню настроек.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        payment_status = self.payment_service.check_payment_status(payment_id)

        if not payment_status:
            await query.edit_message_text(
                "Не удалось проверить статус платежа. Попробуй еще раз через минуту.",
                reply_markup=query.message.reply_markup, # Keep the same keyboard
                parse_mode=ParseMode.HTML,
            )
            return
            
        if payment_status.status == "succeeded":
            # Payment successful
            self.user_service.grant_premium(user, days=30)
            context.user_data.pop("pending_payment_id", None)
            
            await query.edit_message_text(
                "✅ Оплата прошла успешно!\n\n👑 Спасибо за подписку! Тебе доступны все премиум-функции.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        elif payment_status.status == "pending":
            await query.answer("⏳ Платеж еще в обработке. Попробуй проверить снова через минуту.", show_alert=True)
        else: # canceled, failed, etc.
            context.user_data.pop("pending_payment_id", None)
            await query.edit_message_text(
                "❌ Похоже, платеж не прошел или был отменен.\n\nПопробуй еще раз.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )


    async def about_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show information about the bot"""
        query = update.callback_query
        await query.answer()

        about_text = """**О боте**

Я — твоя карманная подружка для самопомощи 💚

Я здесь, чтобы:
- Помочь тебе снять тревогу
- Разобраться в сложных ситуациях
- Услышать саму себя

Я **НЕ** терапевт и не заменяю профессиональную помощь.

Если тебе действительно тяжело — обратись к специалисту:
📞 8-800-2000-122 (бесплатная психологическая помощь)

Версия: **MVP 1.0 (Phase 1)**
Разработчик: AI Friends Team"""

        await query.edit_message_text(about_text, reply_markup=kb.get_back_to_menu_keyboard(),
            parse_mode="Markdown",
        )

    async def insight_card_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle insight card actions (create or skip)"""
        query = update.callback_query
        
        if query.data == "skip_card":
            await query.answer()
            await query.edit_message_text(
                "Без проблем! 😊\n\nЧем ещё могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        if query.data.startswith("create_card_"):
            template = query.data.replace("create_card_", "")
            await self._create_card(update, context, template)

    async def _create_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE, template: str):
        """Handle create insight card request (Phase 2)"""
        query = update.callback_query

        # Check rate limit for cards
        is_allowed, remaining = self._check_rate_limit(context, "cards")
        if not is_allowed:
            await query.answer(
                "Ты создала слишком много карточек за последний час. Попробуй позже!",
                show_alert=True
            )
            return

        await query.answer("Создаю карточку... ✨")

        telegram_user = update.effective_user

        try:
            # Record card creation
            self._record_rate_limit_usage(context, "cards")

            # Get the insight text from context
            insight_text = context.user_data.get("last_insight_text", "")

            if not insight_text:
                await query.edit_message_text(
                    "Упс, не могу найти текст инсайта 😔\n\nПопробуй ещё раз позже.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Generate card image in a separate thread to avoid blocking
            card_image = await asyncio.to_thread(
                self.card_service.generate_insight_card,
                insight_text=insight_text,
                template=template,
            )

            if not card_image:
                await query.edit_message_text(
                    "Что-то пошло не так при создании карточки 😔\n\nПопробуй позже.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Send the card as photo using context manager for safe file handling
            with open(card_image, 'rb') as card_file:
                await query.message.reply_photo(
                    photo=card_file,
                    caption="Вот твоя карточка! Сохрани или поделись в Stories 💚",
                    parse_mode=ParseMode.HTML,
                )

            # Clean up the generated file
            try:
                os.remove(card_image)
            except OSError as e:
                logger.warning(f"Could not remove temporary card file {card_image}: {e}")

            # Show menu
            await query.edit_message_text(
                "Карточка готова! ✨\n\nЧем ещё могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:
            logger.error(f"Error creating insight card: {e}", exc_info=True)
            await query.edit_message_text(
                "Ой, что-то пошло не так 😔\n\nПопробуй позже или выбери другое действие.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error: {context.error}", exc_info=True)

        if update and update.effective_message:
            await update.effective_message.reply_text(
                msg.ERROR_GENERIC,
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
