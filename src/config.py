"""
Configuration management for AI Friends bot
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")

    # AI/LLM
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Database
    database_url: str = Field(default="sqlite:///./aifriends.db", alias="DATABASE_URL")
    chroma_db_path: str = Field(default="./chroma_db", alias="CHROMA_DB_PATH")

    # Rate Limiting
    max_messages_per_hour: int = Field(default=50, alias="MAX_MESSAGES_PER_HOUR")
    max_cards_per_hour: int = Field(default=1, alias="MAX_CARDS_PER_HOUR")

    # Freemium
    free_analysis_per_week: int = Field(default=3, alias="FREE_ANALYSIS_PER_WEEK")

    # Premium
    premium_price_monthly: int = Field(default=990, alias="PREMIUM_PRICE_MONTHLY")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
