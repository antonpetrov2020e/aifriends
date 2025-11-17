"""
Telegram bot handlers for AI Friends bot
Implements Phase 1: Foundation (Onboarding, Panic, Structured Analysis)
Phase 2: Memory & Viral Cards
"""
import asyncio
from typing import List, Dict
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from . import messages as msg
from . import keyboards as kb
from ..services.user_service import UserService
from ..services.ai_service import AIService
from ..database.models import User, Conversation, Message


class BotHandlers:
    """Main bot handlers class"""

    def __init__(
        self,
        db_session: Session,
        ai_service: AIService,
        memory_service,
        card_service,
        free_analysis_limit: int = 3
    ):
        self.db = db_session
        self.user_service = UserService(db_session)
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.card_service = card_service
        self.free_analysis_limit = free_analysis_limit

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - Onboarding flow"""
        telegram_user = update.effective_user

        # Get or create user
        user = self.user_service.get_or_create_user(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )

        # If user already completed onboarding, show main menu
        if user.onboarding_completed:
            await update.message.reply_text("С возвращением! 👋\n\nЧем могу помочь?", reply_markup=kb.get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
            return

        # Start onboarding sequence
        # Step 1: Welcome
        await update.message.reply_text(msg.WELCOME_MESSAGE, parse_mode=ParseMode.HTML)
        await asyncio.sleep(1.5)

        # Step 2: Ethical boundaries
        await update.message.reply_text(msg.ETHICAL_BOUNDARIES, parse_mode=ParseMode.HTML)
        await asyncio.sleep(2)

        # Step 3: Privacy and consent
        await update.message.reply_text(msg.PRIVACY_INTRO + "\n\n" + msg.CONSENT_QUESTION, reply_markup=kb.get_consent_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def consent_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle consent button callback"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        if query.data == "consent_yes":
            # Give consent
            self.user_service.give_consent(user)
            self.user_service.complete_onboarding(user)

            # Show welcome message with main menu
            await query.edit_message_text(msg.CONSENT_ACCEPTED, reply_markup=kb.get_main_menu_keyboard(),
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

    async def _save_conversation_memories(self, user_id: int, conversation_history: List[Dict]):
        """
        Asynchronously save conversation memories
        Called when conversation ends or user returns to menu
        """
        if not conversation_history or len(conversation_history) < 2:
            return

        try:
            # Extract and save memories in background
            await self.memory_service.extract_and_save_from_conversation(
                user_id=user_id,
                conversation=conversation_history,
                ai_service=self.ai_service,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving memories: {e}")

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "back_to_menu":
            # Save memories before returning to menu (Phase 2)
            conversation_history = context.user_data.get("conversation_history", [])
            if conversation_history:
                telegram_user = update.effective_user
                # Save memories asynchronously (don't wait)
                asyncio.create_task(self._save_conversation_memories(
                    user_id=telegram_user.id,
                    conversation_history=conversation_history
                ))

            # Clear conversation context
            context.user_data.pop("conversation_mode", None)
            context.user_data.pop("conversation_history", None)

            await query.edit_message_text("Чем могу помочь?", reply_markup=kb.get_main_menu_keyboard(),
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
            context.user_data["conversation_history"] = []  # Initialize empty history

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
                price=990,  # Premium price
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

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle free-form text messages based on conversation context"""
        text = update.message.text
        conversation_mode = context.user_data.get("conversation_mode")
        waiting_for = context.user_data.get("waiting_for")

        if waiting_for == "situation_details":
            # User provided situation details, now ask about feelings
            # Store situation in context
            context.user_data["current_situation"] = text

            await update.message.reply_text(
                msg.ANALYSIS_FEELINGS_PROMPT,
                reply_markup=kb.get_feelings_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            # Clear waiting state
            context.user_data["waiting_for"] = None

        elif conversation_mode == "panic_talk":
            # In panic talk mode - use AI to provide empathetic response
            conversation_history = context.user_data.get("conversation_history", [])
            telegram_user = update.effective_user

            # Add user message to history
            conversation_history.append({"role": "user", "content": text})

            try:
                # Recall relevant memories (Phase 2)
                memories = await self.memory_service.recall_memories(
                    user_id=telegram_user.id,
                    query=text,
                    n_results=3,
                )
                memory_context = self.memory_service.format_memories_for_context(memories) if memories else ""

                # Get AI response
                response = await self.ai_service.chat(
                    user_message=text,
                    conversation_history=conversation_history[:-1],  # Exclude current message
                    context=f"Пользователь в режиме 'паника' - нужна эмоциональная поддержка, валидация чувств и короткий эмпатичный ответ (2-3 предложения). Не давай советов, просто поддержи.\n\n{memory_context}"
                )

                # Add AI response to history
                conversation_history.append({"role": "assistant", "content": response})
                context.user_data["conversation_history"] = conversation_history

                await update.message.reply_text(response, parse_mode=ParseMode.HTML)

                # Check for insight (don't block on error)
                try:
                    has_insight = await self.ai_service.detect_insight(text)
                    if has_insight:
                        # Save insight text for card generation (Phase 2)
                        context.user_data["last_insight_text"] = text
                        await asyncio.sleep(1)
                        await update.message.reply_text(
                            msg.INSIGHT_DETECTED + "\n\n" + msg.INSIGHT_SHARE_OFFER,
                            reply_markup=kb.get_insight_share_keyboard(),
                            parse_mode=ParseMode.HTML,
                        )
                except:
                    pass  # Silently ignore insight detection errors

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in panic_talk mode: {e}")
                # Show empathetic error message
                await update.message.reply_text(
                    "Слушай, у меня что-то тормозит сейчас 😔\n\nНо я здесь и слышу тебя. Продолжай, если хочешь, или можем вернуться к главному меню.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )

        elif conversation_mode == "thinking_dialogue":
            # User is in thinking dialogue (Socratic method) - use AI
            conversation_history = context.user_data.get("conversation_history", [])
            telegram_user = update.effective_user

            # Add user message to history
            conversation_history.append({"role": "user", "content": text})

            try:
                # Recall relevant memories (Phase 2)
                memories = await self.memory_service.recall_memories(
                    user_id=telegram_user.id,
                    query=text,
                    n_results=3,
                )
                memory_context = self.memory_service.format_memories_for_context(memories) if memories else ""

                # Get AI response with Socratic method
                response = await self.ai_service.chat(
                    user_message=text,
                    conversation_history=conversation_history[:-1],  # Exclude current message
                    context=f"Продолжай задавать короткие наводящие вопросы (1-2 предложения). Помоги пользователю самостоятельно прийти к решению. Не давай прямых советов.\n\n{memory_context}"
                )

                # Add AI response to history
                conversation_history.append({"role": "assistant", "content": response})
                context.user_data["conversation_history"] = conversation_history

                await update.message.reply_text(response, parse_mode=ParseMode.HTML)

                # Check for insight (don't block on error)
                try:
                    has_insight = await self.ai_service.detect_insight(text)
                    if has_insight:
                        # Save insight text for card generation (Phase 2)
                        context.user_data["last_insight_text"] = text
                        await asyncio.sleep(1)
                        await update.message.reply_text(
                            msg.INSIGHT_DETECTED + "\n\n" + msg.INSIGHT_SHARE_OFFER,
                            reply_markup=kb.get_insight_share_keyboard(),
                            parse_mode=ParseMode.HTML,
                        )
                except:
                    pass  # Silently ignore insight detection errors

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in thinking_dialogue mode: {e}")
                # Show empathetic error message
                await update.message.reply_text(
                    "Упс, что-то пошло не так 😔\n\nДавай попробуем ещё раз, или можем вернуться к главному меню.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )

        elif conversation_mode == "journal":
            # User is writing in journal - provide supportive response
            conversation_history = context.user_data.get("conversation_history", [])
            journal_entry_count = context.user_data.get("journal_entry_count", 0)
            telegram_user = update.effective_user

            # Add user message to history
            conversation_history.append({"role": "user", "content": text})

            try:
                # Recall relevant memories (Phase 2)
                memories = await self.memory_service.recall_memories(
                    user_id=telegram_user.id,
                    query=text,
                    n_results=3,
                )
                memory_context = self.memory_service.format_memories_for_context(memories) if memories else ""

                # Get supportive AI response
                response = await self.ai_service.chat(
                    user_message=text,
                    conversation_history=conversation_history[:-1],
                    context=f"Пользователь ведёт личный дневник. Дай короткий (2-3 предложения) эмпатичный ответ. Можешь задать мягкий вопрос для саморефлексии, но не настаивай. Подчеркни важность того, что она делает.\n\n{memory_context}"
                )

                # Add AI response to history
                conversation_history.append({"role": "assistant", "content": response})
                context.user_data["conversation_history"] = conversation_history
                context.user_data["journal_entry_count"] = journal_entry_count + 1

                await update.message.reply_text(response, parse_mode=ParseMode.HTML)

                # After 2-3 entries, offer to finish or continue
                if journal_entry_count >= 2:
                    await asyncio.sleep(1)
                    await update.message.reply_text(
                        msg.JOURNAL_FOLLOW_UP,
                        reply_markup=kb.get_journal_keyboard(),
                        parse_mode=ParseMode.HTML,
                    )

                # Check for insight
                try:
                    has_insight = await self.ai_service.detect_insight(text)
                    if has_insight:
                        await asyncio.sleep(1)
                        await update.message.reply_text(
                            msg.INSIGHT_DETECTED + "\n\n" + msg.INSIGHT_SHARE_OFFER,
                            reply_markup=kb.get_insight_share_keyboard(),
                            parse_mode=ParseMode.HTML,
                        )
                except:
                    pass  # Silently ignore insight detection errors

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in journal mode: {e}")
                await update.message.reply_text(
                    "Ой, что-то у меня сбой 😔\n\nПродолжай писать, если хочешь, или можем вернуться к меню.",
                    reply_markup=kb.get_journal_keyboard(),
                    parse_mode=ParseMode.HTML,
                )

        else:
            # Default: no active conversation
            await update.message.reply_text(
                "Не совсем поняла 🤔\n\nВыбери, пожалуйста, что тебе нужно:",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def feeling_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feeling selection and provide validation"""
        query = update.callback_query
        await query.answer()

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

        # Start Socratic questioning with AI
        feeling_names = {
            "anger": "злость",
            "hurt": "обиду",
            "anxiety": "тревогу",
            "confusion": "растерянность",
            "unknown": "смешанные чувства, которые сложно определить",
        }
        feeling_name = feeling_names.get(feeling, feeling)

        first_question = await self.ai_service.chat(
            user_message=f"Ситуация: {situation}\nЯ чувствую: {feeling_name}",
            conversation_history=[],
            context=f"Пользователь описал ситуацию и выразил чувство. Задай ОДИН короткий (1-2 предложения) наводящий вопрос в стиле Socratic method. Помоги разобраться в её настоящих желаниях, страхах или границах. Не повторяй ситуацию, не давай советов - только вопрос."
        )

        await query.message.reply_text(first_question, parse_mode=ParseMode.HTML)

        # Initialize conversation history
        context.user_data["conversation_history"] = [
            {"role": "user", "content": f"Ситуация: {situation}\nЯ чувствую: {feeling_name}"},
            {"role": "assistant", "content": first_question}
        ]

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
            # Show premium features
            premium_text = """👑 **Premium подписка**

**990₽/месяц**

Что входит:
✅ Безлимитные "Разборы полетов"
✅ Расширенная память обо всех наших разговорах
✅ Премиум-шаблоны для карточек инсайтов
✅ Приоритетная поддержка

_Функция оплаты появится в следующей версии_"""

            await query.edit_message_text(premium_text, reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode="Markdown",
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

    async def create_card_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle create insight card request (Phase 2)"""
        query = update.callback_query
        await query.answer("Создаю карточку... ✨")

        telegram_user = update.effective_user

        try:
            # Get the insight text from context
            insight_text = context.user_data.get("last_insight_text", "")

            if not insight_text:
                await query.edit_message_text(
                    "Упс, не могу найти текст инсайта 😔\n\nПопробуй ещё раз позже.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Generate card image
            card_image = await self.card_service.generate_insight_card(
                insight_text=insight_text,
                template="minimalist",
            )

            if not card_image:
                await query.edit_message_text(
                    "Что-то пошло не так при создании карточки 😔\n\nПопробуй позже.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Send the card as photo
            await query.message.reply_photo(
                photo=card_image,
                caption="Вот твоя карточка! Сохрани или поделись в Stories 💚",
                parse_mode=ParseMode.HTML,
            )

            # Show menu
            await query.edit_message_text(
                "Карточка готова! ✨\n\nЧем ещё могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating insight card: {e}")
            import traceback
            logger.error(traceback.format_exc())

            await query.edit_message_text(
                "Ой, что-то пошло не так 😔\n\nПопробуй позже или выбери другое действие.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        print(f"Error: {context.error}")

        if update.effective_message:
            await update.effective_message.reply_text(
                msg.ERROR_GENERIC,
                reply_markup=kb.get_back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
