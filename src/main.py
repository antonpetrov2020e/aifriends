"""
AI Friends Bot - Main entry point
Phase 1 MVP: Foundation with Onboarding, Panic Button, and Structured Analysis
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from .config import settings
from .database import init_db, get_session
from .bot.handlers import BotHandlers
from .services.ai_service import AIService
from .services.memory_service import MemoryService
from .services.card_service import CardService
from .services.payment_service import PaymentService
from .services.gratitude_service import GratitudeService


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.log_level),
)
logger = logging.getLogger(__name__)


def main():
    """Main function to start the bot"""

    # Initialize database
    logger.info("Initializing database...")
    engine = init_db(settings.database_url)
    db_session = get_session(engine)

    # Initialize AI service
    logger.info("Initializing AI service...")
    logger.info(f"Using model: {settings.llm_model}")
    ai_service = AIService(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
    )

    # Initialize Memory service (Phase 2)
    logger.info("Initializing Memory service...")
    memory_service = MemoryService(chroma_db_path=settings.chroma_db_path)

    # Initialize Card service (Phase 2)
    logger.info("Initializing Card service...")
    card_service = CardService()

    # Initialize Payment service (Phase 3)
    payment_service = None
    if settings.yookassa_shop_id and settings.yookassa_secret_key:
        logger.info("Initializing Payment service...")
        payment_service = PaymentService(
            db_session=db_session,
            shop_id=settings.yookassa_shop_id,
            secret_key=settings.yookassa_secret_key,
        )
    else:
        logger.warning("YooKassa credentials not configured - payment features disabled")

    # Initialize Gratitude service (Phase 3)
    logger.info("Initializing Gratitude service...")
    gratitude_service = GratitudeService(db_session=db_session)

    # Initialize handlers
    logger.info("Initializing bot handlers...")
    handlers = BotHandlers(
        db_session=db_session,
        ai_service=ai_service,
        memory_service=memory_service,
        card_service=card_service,
        payment_service=payment_service,
        gratitude_service=gratitude_service,
        free_analysis_limit=settings.free_analysis_per_week,
    )

    # Create application
    logger.info("Creating Telegram application...")
    app_builder = Application.builder().token(settings.telegram_bot_token)

    # Configure proxy if enabled
    if settings.proxy_enabled and settings.proxy_url:
        logger.info(f"Using proxy: {settings.proxy_url.split('@')[1] if '@' in settings.proxy_url else settings.proxy_url}")
        # Configure proxy for httpx (used by python-telegram-bot)
        import httpx
        proxy_config = httpx.Proxy(settings.proxy_url)
        app_builder = app_builder.proxy(proxy_config)

    application = app_builder.build()

    # Register command handlers
    application.add_handler(CommandHandler("start", handlers.start_command))

    # Register callback query handlers
    # Onboarding callbacks (NEW)
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern="^show_features$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern="^skip_to_panic$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern="^skip_onboarding$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern="^first_need_")
    )

    # Consent callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.consent_callback, pattern="^consent_")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.consent_callback, pattern="^privacy_policy$")
    )

    # Main menu callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.main_menu_callback, pattern="^back_to_menu$")
    )

    # Panic button callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.panic_button, pattern="^panic$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.panic_response_callback, pattern="^panic_")
    )

    # Analysis callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.analysis_start, pattern="^analysis_start$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.situation_callback, pattern="^situation_")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.feeling_callback, pattern="^feeling_")
    )

    # Settings callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern="^settings$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern="^delete_history$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern="^premium$")
    )

    # About callback
    application.add_handler(
        CallbackQueryHandler(handlers.about_callback, pattern="^about$")
    )

    # Journal callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.journal_start, pattern="^journal$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.journal_callback, pattern="^journal_")
    )

    # Delete confirmation callback
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern="^confirm_delete$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern="^notifications$")
    )

    # Navigation callbacks (back_to_analysis, continue_talk)
    application.add_handler(
        CallbackQueryHandler(handlers.navigation_callback, pattern="^back_to_analysis$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.navigation_callback, pattern="^continue_talk$")
    )

    # Card callbacks (create_card, skip_card) - Phase 2
    application.add_handler(
        CallbackQueryHandler(handlers.insight_card_callback, pattern="^skip_card$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.insight_card_callback, pattern="^create_card$")
    )
    # Template selection callback (Phase 3)
    application.add_handler(
        CallbackQueryHandler(handlers.template_selection_callback, pattern="^template_")
    )

    # Premium callbacks (Phase 3)
    application.add_handler(
        CallbackQueryHandler(handlers.premium_callback, pattern="^premium$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.buy_premium_callback, pattern="^buy_premium$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.cancel_premium_callback, pattern="^cancel_premium$")
    )

    # Gratitude callbacks (Phase 3)
    application.add_handler(
        CallbackQueryHandler(handlers.gratitude_callback, pattern="^gratitude$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.gratitude_new_callback, pattern="^gratitude_new$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.gratitude_history_callback, pattern="^gratitude_history$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.gratitude_week_summary_callback, pattern="^gratitude_week_summary$")
    )

    # Mood tracking callbacks (Phase 3)
    application.add_handler(
        CallbackQueryHandler(handlers.mood_track_callback, pattern="^mood_track$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.mood_save_callback, pattern="^mood_save_")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.mood_graph_callback, pattern="^mood_graph$")
    )

    # Text message handler (for free-form responses)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message)
    )

    # Error handler
    application.add_error_handler(handlers.error_handler)

    # Start the bot
    logger.info("Starting bot polling...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
