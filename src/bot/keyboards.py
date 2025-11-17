"""
Telegram keyboard layouts for bot navigation
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for privacy consent"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Согласна, погнали!", callback_data="consent_yes"),
        ],
        [
            InlineKeyboardButton("📄 Сначала почитать политику", callback_data="privacy_policy"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu with core features"""
    keyboard = [
        [
            InlineKeyboardButton("😱 Паника!", callback_data="panic"),
        ],
        [
            InlineKeyboardButton("🕵️‍♀️ Разбор полетов", callback_data="analysis_start"),
        ],
        [
            InlineKeyboardButton("🧘‍♀️ Фокус на себя", callback_data="journal"),
        ],
        [
            InlineKeyboardButton("ℹ️ О боте", callback_data="about"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_analysis_situation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting situation type"""
    keyboard = [
        [
            InlineKeyboardButton("💔 Он не пишет", callback_data="situation_no_message"),
        ],
        [
            InlineKeyboardButton("😡 Мы поссорились", callback_data="situation_fight"),
        ],
        [
            InlineKeyboardButton("🤔 Он сказал что-то странное", callback_data="situation_strange"),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Другое...", callback_data="situation_other"),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_feelings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting feelings"""
    keyboard = [
        [
            InlineKeyboardButton("😠 Злость", callback_data="feeling_anger"),
            InlineKeyboardButton("😢 Обида", callback_data="feeling_hurt"),
        ],
        [
            InlineKeyboardButton("😰 Тревога", callback_data="feeling_anxiety"),
            InlineKeyboardButton("🤯 Растерянность", callback_data="feeling_confusion"),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Не знаю", callback_data="feeling_unknown"),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data="back_to_analysis"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_panic_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for panic mode"""
    keyboard = [
        [
            InlineKeyboardButton("💚 Да, немного лучше", callback_data="panic_better"),
        ],
        [
            InlineKeyboardButton("💔 Еще тяжело", callback_data="panic_continue"),
        ],
        [
            InlineKeyboardButton("✍️ Хочу выговориться", callback_data="panic_talk"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_insight_share_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for offering to create shareable card"""
    keyboard = [
        [
            InlineKeyboardButton("✨ Да, сделай картинку!", callback_data="create_card"),
        ],
        [
            InlineKeyboardButton("🙈 Нет, спасибо", callback_data="skip_card"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings menu"""
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Удалить мою историю", callback_data="delete_history"),
        ],
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="notifications"),
        ],
        [
            InlineKeyboardButton("👑 Premium", callback_data="premium"),
        ],
        [
            InlineKeyboardButton("« Назад в меню", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Simple back button"""
    keyboard = [
        [
            InlineKeyboardButton("« Вернуться в меню", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_continue_or_menu_keyboard() -> InlineKeyboardMarkup:
    """Continue conversation or go back to menu"""
    keyboard = [
        [
            InlineKeyboardButton("💬 Продолжить разговор", callback_data="continue_talk"),
        ],
        [
            InlineKeyboardButton("✅ Понятно, спасибо", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


# Onboarding Tour Keyboards

def get_tour_offer_keyboard() -> InlineKeyboardMarkup:
    """Offer to start interactive tour"""
    keyboard = [
        [
            InlineKeyboardButton("✨ Да, покажи!", callback_data="tour_start"),
        ],
        [
            InlineKeyboardButton("Потом, хочу в меню", callback_data="tour_skip"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tour_next_keyboard(next_step: str) -> InlineKeyboardMarkup:
    """Next button for tour progression"""
    keyboard = [
        [
            InlineKeyboardButton("Дальше →", callback_data=f"tour_{next_step}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tour_complete_keyboard() -> InlineKeyboardMarkup:
    """Complete tour and go to main menu"""
    keyboard = [
        [
            InlineKeyboardButton("Понятно! 💪", callback_data="tour_complete"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
