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
from .bot import constants as c
from .services.ai_service import AIService
from .services.memory_service import MemoryService
from .services.card_service import CardService
from .services.payment_service import payment_service


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
    card_service = CardService(generated_cards_path=settings.generated_cards_path)

    # Initialize handlers
    logger.info("Initializing bot handlers...")
    handlers = BotHandlers(
        db_session=db_session,
        ai_service=ai_service,
        memory_service=memory_service,
        card_service=card_service,
        payment_service=payment_service,
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
        CallbackQueryHandler(handlers.onboarding_callback, pattern=f"^{c.SHOW_FEATURES}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern=f"^{c.SKIP_TO_PANIC}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern=f"^{c.SKIP_ONBOARDING}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.onboarding_callback, pattern=f"^{c.FIRST_NEED_PREFIX}")
    )

    # Consent callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.consent_callback, pattern=f"^{c.CONSENT_PREFIX}")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.consent_callback, pattern=f"^{c.PRIVACY_POLICY}$")
    )

    # Main menu callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.main_menu_callback, pattern=f"^{c.BACK_TO_MENU}$")
    )

    # Panic button callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.panic_button, pattern=f"^{c.PANIC}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.panic_response_callback, pattern=f"^{c.PANIC_PREFIX}")
    )

    # Analysis callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.analysis_start, pattern=f"^{c.ANALYSIS_START}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.situation_callback, pattern=f"^{c.SITUATION_PREFIX}")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.feeling_callback, pattern=f"^{c.FEELING_PREFIX}")
    )

    # Settings callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern=f"^{c.SETTINGS}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern=f"^{c.DELETE_HISTORY}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern=f"^{c.PREMIUM}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.check_payment_callback, pattern=f"^{c.CHECK_PAYMENT}$")
    )

    # About callback
    application.add_handler(
        CallbackQueryHandler(handlers.about_callback, pattern=f"^{c.ABOUT}$")
    )

    # Journal callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.journal_start, pattern=f"^{c.JOURNAL}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.journal_callback, pattern=f"^{c.JOURNAL_PREFIX}")
    )

    # Diary of Wins callbacks (Phase 3)
    application.add_handler(
        CallbackQueryHandler(handlers.wins_callback, pattern=f"^{c.DIARY_OF_WINS}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.wins_callback, pattern=f"^{c.ADD_WIN}$")
    )

    # Delete confirmation callback
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern=f"^{c.CONFIRM_DELETE}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.settings_callback, pattern=f"^{c.NOTIFICATIONS}$")
    )

    # Navigation callbacks (back_to_analysis, continue_talk)
    application.add_handler(
        CallbackQueryHandler(handlers.navigation_callback, pattern=f"^{c.BACK_TO_ANALYSIS}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.navigation_callback, pattern=f"^{c.CONTINUE_TALK}$")
    )

    # Card callbacks (create_card, skip_card) - Phase 2
    application.add_handler(
        CallbackQueryHandler(handlers.insight_card_callback, pattern=f"^{c.SKIP_CARD}$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.insight_card_callback, pattern=f"^{c.CREATE_CARD_PREFIX}")
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
