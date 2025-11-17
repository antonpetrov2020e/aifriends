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

    # Initialize handlers
    logger.info("Initializing bot handlers...")
    handlers = BotHandlers(
        db_session=db_session,
        ai_service=ai_service,
        free_analysis_limit=settings.free_analysis_per_week,
    )

    # Create application
    logger.info("Creating Telegram application...")
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", handlers.start_command))

    # Register callback query handlers
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

    # Journal callback (placeholder for Phase 2)
    application.add_handler(
        CallbackQueryHandler(
            lambda u, c: u.callback_query.answer(
                "Дневник появится в следующей версии! 📔", show_alert=True
            ),
            pattern="^journal$",
        )
    )

    # Generic continue/skip callbacks
    application.add_handler(
        CallbackQueryHandler(handlers.main_menu_callback, pattern="^continue_talk$")
    )
    application.add_handler(
        CallbackQueryHandler(handlers.main_menu_callback, pattern="^skip_card$")
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
