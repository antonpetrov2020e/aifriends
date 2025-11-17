#!/usr/bin/env python3
"""Quick config checker"""
import sys

try:
    from src.config import settings

    print("=" * 50)
    print("CONFIG CHECK")
    print("=" * 50)

    # Check Telegram token
    has_tg = settings.telegram_bot_token and len(settings.telegram_bot_token) > 20
    print(f"Telegram Bot Token: {'✅ OK' if has_tg else '❌ MISSING'}")

    # Check OpenRouter key
    has_or = settings.openrouter_api_key and 'your_' not in settings.openrouter_api_key
    print(f"OpenRouter API Key: {'✅ OK' if has_or else '❌ MISSING'}")

    if not has_or:
        print("\n⚠️  Нужно добавить OpenRouter API ключ в .env:")
        print("   1. Зайдите на https://openrouter.ai")
        print("   2. Sign In (через Google/GitHub)")
        print("   3. Keys → Create Key")
        print("   4. Скопируйте ключ (начинается с sk-or-)")
        print("   5. Добавьте в .env файл")
        sys.exit(1)

    print(f"Model: {settings.llm_model}")
    print("\n✅ Все ключи настроены! Можно запускать бота.")
    print("   Команда: python -m src.main")

except Exception as e:
    print(f"\n❌ Ошибка загрузки конфигурации: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
