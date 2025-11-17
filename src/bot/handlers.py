"""
Telegram bot handlers for AI Friends bot
Implements Phase 1: Foundation (Onboarding, Panic, Structured Analysis)
"""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session

from . import messages as msg
from . import keyboards as kb
from ..services.user_service import UserService
from ..database.models import User


class BotHandlers:
    """Main bot handlers class"""

    def __init__(self, db_session: Session, free_analysis_limit: int = 3):
        self.db = db_session
        self.user_service = UserService(db_session)
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
            await update.message.reply_text(
                "С возвращением! 👋\n\nЧем могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
            )
            return

        # Start onboarding sequence
        # Step 1: Welcome
        await update.message.reply_text(msg.WELCOME_MESSAGE)
        await asyncio.sleep(1.5)

        # Step 2: Ethical boundaries
        await update.message.reply_text(msg.ETHICAL_BOUNDARIES)
        await asyncio.sleep(2)

        # Step 3: Privacy and consent
        await update.message.reply_text(
            msg.PRIVACY_INTRO + "\n\n" + msg.CONSENT_QUESTION,
            reply_markup=kb.get_consent_keyboard(),
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
            await query.edit_message_text(
                msg.CONSENT_ACCEPTED,
                reply_markup=kb.get_main_menu_keyboard(),
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

            await query.edit_message_text(
                privacy_text,
                reply_markup=kb.get_consent_keyboard(),
                parse_mode="Markdown",
            )

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "back_to_menu":
            await query.edit_message_text(
                "Чем могу помочь?",
                reply_markup=kb.get_main_menu_keyboard(),
            )

    async def panic_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Panic button - immediate anxiety relief"""
        query = update.callback_query
        await query.answer()

        # Phase 1: Static calming response
        await query.edit_message_text(msg.PANIC_GREETING)
        await asyncio.sleep(2)

        await query.message.reply_text(msg.PANIC_BREATHING)
        await asyncio.sleep(6)

        await query.message.reply_text(
            msg.PANIC_CHECK_IN,
            reply_markup=kb.get_panic_keyboard(),
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

            await query.edit_message_text(
                response,
                reply_markup=kb.get_continue_or_menu_keyboard(),
            )

        elif query.data == "panic_continue":
            # Repeat breathing exercise
            await query.edit_message_text(
                "Понимаю. Давай еще раз, медленно 💙",
            )
            await asyncio.sleep(1)
            await query.message.reply_text(msg.PANIC_BREATHING)
            await asyncio.sleep(6)
            await query.message.reply_text(
                msg.PANIC_CHECK_IN,
                reply_markup=kb.get_panic_keyboard(),
            )

        elif query.data == "panic_talk":
            # Switch to free-form conversation mode
            await query.edit_message_text(
                "Я слушаю тебя 👂\n\nПиши всё, что хочешь. Без фильтров.",
            )
            # Set context for conversation tracking
            context.user_data["conversation_mode"] = "panic_talk"

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
            await query.edit_message_text(
                limit_msg,
                reply_markup=kb.get_back_to_menu_keyboard(),
            )
            return

        # Increment counter
        self.user_service.increment_analysis_count(user)

        # Show remaining count for free users
        remaining_text = ""
        if not user.is_premium and remaining > 0:
            remaining_text = f"\n\n_Осталось бесплатных разборов на неделю: {remaining - 1}_"

        # Start analysis flow
        await query.edit_message_text(
            msg.ANALYSIS_INTRO + remaining_text,
            reply_markup=kb.get_analysis_situation_keyboard(),
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

        await query.edit_message_text(response)

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
            await update.message.reply_text(
                msg.ANALYSIS_FEELINGS_PROMPT,
                reply_markup=kb.get_feelings_keyboard(),
            )
            # Clear waiting state
            context.user_data["waiting_for"] = None

        elif conversation_mode == "panic_talk":
            # In panic talk mode - provide validation
            response = """Я слышу тебя 💙

Спасибо, что доверяешь мне это.

Хочешь продолжить или попробуем разобрать ситуацию структурно?"""

            await update.message.reply_text(
                response,
                reply_markup=kb.get_continue_or_menu_keyboard(),
            )

        elif conversation_mode == "thinking_dialogue":
            # User is in thinking dialogue (Socratic method)
            # Phase 1: Simple validation
            response = """Хорошая мысль.

А теперь вопрос: что ты сама хочешь с этим сделать?"""

            await update.message.reply_text(response)

        else:
            # Default: no active conversation
            await update.message.reply_text(
                "Не совсем поняла 🤔\n\nВыбери, пожалуйста, что тебе нужно:",
                reply_markup=kb.get_main_menu_keyboard(),
            )

    async def feeling_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle feeling selection and provide validation"""
        query = update.callback_query
        await query.answer()

        feeling = query.data.replace("feeling_", "")
        context.user_data["current_feeling"] = feeling

        # Provide validation based on feeling
        if feeling == "anger":
            response = msg.FEELING_ANGER
        elif feeling == "hurt":
            response = msg.FEELING_HURT
        elif feeling == "anxiety":
            response = msg.FEELING_ANXIETY
        elif feeling == "confusion":
            response = msg.FEELING_CONFUSION
        else:  # unknown
            response = """Это нормально — не всегда понимать, что чувствуешь.

Иногда это микс из всего сразу.

Давай попробуем разложить по полочкам?"""

        await query.edit_message_text(response)
        await asyncio.sleep(2)

        # Start Socratic questioning (Phase 1: basic version)
        await query.message.reply_text(msg.THINKING_WHAT_DO_YOU_WANT)

        # Set conversation mode for thinking dialogue
        context.user_data["conversation_mode"] = "thinking_dialogue"

    async def settings_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings menu"""
        query = update.callback_query
        await query.answer()

        if query.data == "settings":
            await query.edit_message_text(
                "⚙️ **Настройки**",
                reply_markup=kb.get_settings_keyboard(),
                parse_mode="Markdown",
            )

        elif query.data == "delete_history":
            # Confirm deletion
            confirm_text = """⚠️ **Удаление истории**

Ты уверена? Это действие нельзя отменить.

Будут удалены:
- Вся история разговоров
- Все воспоминания
- Все созданные карточки

Твой аккаунт останется, но мы начнем с чистого листа."""

            confirm_keyboard = [
                [
                    {"text": "❌ Да, удалить всё", "callback_data": "confirm_delete"},
                ],
                [
                    {"text": "« Отмена", "callback_data": "settings"},
                ],
            ]

            await query.edit_message_text(
                confirm_text,
                reply_markup=kb.get_settings_keyboard(),
                parse_mode="Markdown",
            )

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

            await query.edit_message_text(
                premium_text,
                reply_markup=kb.get_back_to_menu_keyboard(),
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

        await query.edit_message_text(
            about_text,
            reply_markup=kb.get_back_to_menu_keyboard(),
            parse_mode="Markdown",
        )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        print(f"Error: {context.error}")

        if update.effective_message:
            await update.effective_message.reply_text(
                msg.ERROR_GENERIC,
                reply_markup=kb.get_back_to_menu_keyboard(),
            )
