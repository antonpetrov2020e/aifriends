"""
Configuration management for AI Friends bot
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")

    # Proxy (for accessing Telegram API if blocked)
    proxy_enabled: bool = Field(default=False, alias="PROXY_ENABLED")
    proxy_url: str = Field(default="", alias="PROXY_URL")

    # AI/LLM
    # OpenRouter (primary provider)
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    llm_model: str = Field(default="google/gemini-2.0-flash-exp:free", alias="LLM_MODEL")

    # Alternative providers (optional)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Voice transcription (Groq Whisper - free and fast)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    whisper_enabled: bool = Field(default=True, alias="WHISPER_ENABLED")

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(default="sqlite:///./aifriends.db", alias="DATABASE_URL")
    chroma_db_path: str = Field(default="./chroma_db", alias="CHROMA_DB_PATH")
    generated_cards_path: str = Field(default="./generated_cards", alias="GENERATED_CARDS_PATH")

    # Rate Limiting
    max_messages_per_hour: int = Field(default=50, alias="MAX_MESSAGES_PER_HOUR")
    max_cards_per_hour: int = Field(default=1, alias="MAX_CARDS_PER_HOUR")

    # Freemium
    free_analysis_per_week: int = Field(default=3, alias="FREE_ANALYSIS_PER_WEEK")

    # Premium
    premium_price_monthly: int = Field(default=990, alias="PREMIUM_PRICE_MONTHLY")
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", alias="YOOKASSA_SECRET_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
