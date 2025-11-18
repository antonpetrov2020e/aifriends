"""
Phase 3 handlers: Premium, Gratitude, Mood tracking
Extension to main BotHandlers class
"""
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import messages as msg
from . import keyboards as kb


class Phase3HandlersMixin:
    """
    Mixin class for Phase 3 handlers
    To be mixed into BotHandlers class
    """

    # Premium handlers

    async def premium_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Premium button in settings"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Check if user already has Premium
        if self.user_service.is_premium(user):
            # Show Premium status
            expires_date = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "навсегда"
            status_text = f"""<b>👑 Premium активен!</b>

Твой Premium активен до {expires_date}.

Что входит:
✅ Безлимитные "Разборы"
✅ Премиум-шаблоны карточек
✅ Расширенная память

Спасибо за поддержку! 💚"""

            await query.edit_message_text(
                status_text,
                reply_markup=kb.get_premium_active_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        else:
            # Show Premium info
            await query.edit_message_text(
                msg.PREMIUM_INFO,
                reply_markup=kb.get_premium_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def buy_premium_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle buy Premium button"""
        query = update.callback_query
        await query.answer("Создаю платеж...")

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        try:
            # Create payment via PaymentService
            payment = await self.payment_service.create_payment(
                user=user,
                amount=99000,  # 990₽ in kopecks
                description="AI Friends Premium - 1 месяц"
            )

            if not payment or not payment.confirmation_url:
                await query.edit_message_text(
                    "❌ Ошибка при создании платежа. Попробуй позже или напиши в поддержку.",
                    reply_markup=kb.get_back_to_menu_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
                return

            # Show payment link
            await query.edit_message_text(
                msg.PREMIUM_PAYMENT_CREATED,
                reply_markup=kb.get_payment_keyboard(payment.confirmation_url),
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating payment: {e}")

            await query.edit_message_text(
                "❌ Что-то пошло не так. Попробуй позже.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    async def cancel_premium_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle cancel Premium subscription"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Cancel subscription
        success = await self.payment_service.cancel_subscription(user)

        if success:
            await query.edit_message_text(
                "Подписка отменена 💔\n\nВсе твои данные сохранены. Ты можешь возобновить Premium в любой момент.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при отмене подписки. Попробуй позже.",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )

    # Gratitude handlers

    async def gratitude_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Gratitude button in main menu"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            msg.GRATITUDE_INTRO,
            reply_markup=kb.get_gratitude_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def gratitude_new_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start new gratitude entry"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Check if already saved today
        today_entry = self.gratitude_service.get_today_gratitude(user)

        if today_entry:
            await query.edit_message_text(
                msg.GRATITUDE_ALREADY_TODAY.format(content=today_entry.content),
                reply_markup=kb.get_gratitude_saved_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        # Ask for gratitude
        await query.edit_message_text(
            msg.GRATITUDE_INTRO,
            parse_mode=ParseMode.HTML,
        )

        # Set context to wait for gratitude text
        context.user_data["waiting_for"] = "gratitude"

    async def gratitude_history_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show gratitude history"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Get all gratitudes
        gratitudes = self.gratitude_service.get_all_gratitudes(user, limit=10)

        if not gratitudes:
            await query.edit_message_text(
                msg.GRATITUDE_HISTORY_EMPTY,
                reply_markup=kb.get_gratitude_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        # Format history
        history_lines = []
        for entry in gratitudes:
            date_str = entry.created_at.strftime("%d.%m.%Y")
            history_lines.append(f"<b>{date_str}:</b> {entry.content}")

        history_text = "<b>📜 Твои благодарности:</b>\n\n" + "\n\n".join(history_lines[:10])

        await query.edit_message_text(
            history_text,
            reply_markup=kb.get_gratitude_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def gratitude_week_summary_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate week summary"""
        query = update.callback_query
        await query.answer("Генерирую резюме...")

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Generate AI summary
        summary = await self.gratitude_service.generate_week_summary(user, self.ai_service)

        await query.edit_message_text(
            msg.GRATITUDE_WEEK_SUMMARY.format(summary=summary),
            reply_markup=kb.get_gratitude_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    # Mood tracking handlers

    async def mood_track_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Mood tracking button"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            msg.MOOD_INTRO,
            reply_markup=kb.get_mood_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def mood_save_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Save mood (1, 2, or 3)"""
        query = update.callback_query
        await query.answer()

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Extract mood value from callback_data
        mood = int(query.data.split("_")[1])  # "mood_1" -> 1

        # Save mood
        self.gratitude_service.save_mood(user, mood)

        mood_emojis = {1: "😔", 2: "😐", 3: "😊"}
        await query.edit_message_text(
            msg.MOOD_SAVED,
            reply_markup=kb.get_mood_saved_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    async def mood_graph_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show mood graph"""
        query = update.callback_query
        await query.answer("Генерирую график...")

        telegram_user = update.effective_user
        user = self.user_service.get_or_create_user(telegram_id=telegram_user.id)

        # Get week moods
        moods = self.gratitude_service.get_week_moods(user)

        if not moods:
            await query.edit_message_text(
                "У тебя пока нет отметок настроения.\n\nНачни отмечать каждый день!",
                reply_markup=kb.get_back_to_menu_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            return

        # Format graph
        graph = self.gratitude_service.format_mood_graph(moods)
        avg_mood = self.gratitude_service.get_average_mood(user, days=7)

        # Generate insights
        insights = await self.gratitude_service.generate_mood_insights(user, self.ai_service)

        avg_emoji = "😔" if avg_mood < 1.7 else ("😐" if avg_mood < 2.4 else "😊")

        await query.edit_message_text(
            msg.MOOD_WEEK_GRAPH.format(
                graph=graph,
                avg_mood=f"{avg_emoji} {avg_mood:.1f}/3.0",
                insights=insights
            ),
            reply_markup=kb.get_back_to_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
