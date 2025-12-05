"""
Telegram keyboard layouts for bot navigation
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from . import constants as c


def get_show_features_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for choosing to see features or skip"""
    keyboard = [
        [
            InlineKeyboardButton("👀 Да, покажи быстро", callback_data=c.SHOW_FEATURES),
        ],
        [
            InlineKeyboardButton("😱 Мне срочно нужна помощь!", callback_data=c.SKIP_TO_PANIC),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Сразу к главному меню", callback_data=c.SKIP_ONBOARDING),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for privacy consent"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, согласна", callback_data=c.CONSENT_YES),
        ],
        [
            InlineKeyboardButton("📄 Почитать политику", callback_data=c.PRIVACY_POLICY),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_first_need_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for first interaction after onboarding"""
    keyboard = [
        [
            InlineKeyboardButton("🕵️‍♀️ Хочу разобраться в ситуации", callback_data=c.FIRST_NEED_ANALYSIS),
        ],
        [
            InlineKeyboardButton("😱 Мне тревожно/паника", callback_data=c.FIRST_NEED_PANIC),
        ],
        [
            InlineKeyboardButton("🧘‍♀️ Хочу просто записать мысли", callback_data=c.FIRST_NEED_JOURNAL),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Просто смотрю, что тут", callback_data=c.FIRST_NEED_EXPLORE),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu with core features"""
    keyboard = [
        [
            InlineKeyboardButton("😱 Паника!", callback_data=c.PANIC),
            InlineKeyboardButton("🕵️‍♀️ Разбор полетов", callback_data=c.ANALYSIS_START),
        ],
        [
            InlineKeyboardButton("🏆 Дневник побед", callback_data=c.DIARY_OF_WINS),
            InlineKeyboardButton("🧘‍♀️ Фокус на себя", callback_data=c.JOURNAL),
        ],
        [
            InlineKeyboardButton("ℹ️ О боте", callback_data=c.ABOUT),
            InlineKeyboardButton("⚙️ Настройки", callback_data=c.SETTINGS),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_analysis_situation_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting situation type"""
    keyboard = [
        [
            InlineKeyboardButton("💔 Он не пишет", callback_data=c.SITUATION_NO_MESSAGE),
        ],
        [
            InlineKeyboardButton("😡 Мы поссорились", callback_data=c.SITUATION_FIGHT),
        ],
        [
            InlineKeyboardButton("🤔 Он сказал что-то странное", callback_data=c.SITUATION_STRANGE),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Другое...", callback_data=c.SITUATION_OTHER),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_feelings_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting feelings"""
    keyboard = [
        [
            InlineKeyboardButton("😠 Злость", callback_data=c.FEELING_ANGER),
            InlineKeyboardButton("😢 Обида", callback_data=c.FEELING_HURT),
        ],
        [
            InlineKeyboardButton("😰 Тревога", callback_data=c.FEELING_ANXIETY),
            InlineKeyboardButton("🤯 Растерянность", callback_data=c.FEELING_CONFUSION),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Не знаю", callback_data=c.FEELING_UNKNOWN),
        ],
        [
            InlineKeyboardButton("« Назад", callback_data=c.BACK_TO_ANALYSIS),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_panic_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for panic mode"""
    keyboard = [
        [
            InlineKeyboardButton("💚 Да, немного лучше", callback_data=c.PANIC_BETTER),
        ],
        [
            InlineKeyboardButton("💔 Еще тяжело", callback_data=c.PANIC_CONTINUE),
        ],
        [
            InlineKeyboardButton("✍️ Хочу выговориться", callback_data=c.PANIC_TALK),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_insight_share_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for offering to create shareable card"""
    keyboard = [
        [
            InlineKeyboardButton("✨ Да, сделай картинку!", callback_data=c.CREATE_CARD_MINIMALIST),
        ],
        [
            InlineKeyboardButton("🙈 Нет, спасибо", callback_data=c.SKIP_CARD),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_premium_card_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for offering premium card templates."""
    keyboard = [
        [
            InlineKeyboardButton("Минимализм", callback_data=c.CREATE_CARD_MINIMALIST),
            InlineKeyboardButton("✨ Градиент", callback_data=c.CREATE_CARD_GRADIENT),
        ],
        [
            InlineKeyboardButton("🙈 Нет, спасибо", callback_data=c.SKIP_CARD),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings menu"""
    keyboard = [
        [
            InlineKeyboardButton("🗑️ Удалить мою историю", callback_data=c.DELETE_HISTORY),
        ],
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data=c.NOTIFICATIONS),
        ],
        [
            InlineKeyboardButton("👑 Premium", callback_data=c.PREMIUM),
        ],
        [
            InlineKeyboardButton("« Назад в меню", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Simple back button"""
    keyboard = [
        [
            InlineKeyboardButton("« Вернуться в меню", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_continue_or_menu_keyboard() -> InlineKeyboardMarkup:
    """Continue conversation or go back to menu"""
    keyboard = [
        [
            InlineKeyboardButton("💬 Продолжить разговор", callback_data=c.CONTINUE_TALK),
        ],
        [
            InlineKeyboardButton("✅ Понятно, спасибо", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_journal_keyboard() -> InlineKeyboardMarkup:
    """Journal mode keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✍️ Продолжить писать", callback_data=c.JOURNAL_CONTINUE),
        ],
        [
            InlineKeyboardButton("✅ Достаточно на сегодня", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wins_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for the Diary of Wins feature."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить победу", callback_data=c.ADD_WIN),
        ],
        [
            InlineKeyboardButton("« Назад в меню", callback_data=c.BACK_TO_MENU),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm deletion keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("❌ Да, удалить всё", callback_data=c.CONFIRM_DELETE),
        ],
        [
            InlineKeyboardButton("« Отмена", callback_data=c.SETTINGS),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
