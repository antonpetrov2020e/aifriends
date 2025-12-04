"""
Telegram keyboard layouts for bot navigation
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_show_features_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for choosing to see features or skip"""
    keyboard = [
        [
            InlineKeyboardButton("👀 Да, покажи быстро", callback_data="show_features"),
        ],
        [
            InlineKeyboardButton("😱 Мне срочно нужна помощь!", callback_data="skip_to_panic"),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Сразу к главному меню", callback_data="skip_onboarding"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for privacy consent"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, согласна", callback_data="consent_yes"),
        ],
        [
            InlineKeyboardButton("📄 Почитать политику", callback_data="privacy_policy"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_first_need_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for first interaction after onboarding"""
    keyboard = [
        [
            InlineKeyboardButton("🕵️‍♀️ Хочу разобраться в ситуации", callback_data="first_need_analysis"),
        ],
        [
            InlineKeyboardButton("😱 Мне тревожно/паника", callback_data="first_need_panic"),
        ],
        [
            InlineKeyboardButton("🧘‍♀️ Хочу просто записать мысли", callback_data="first_need_journal"),
        ],
        [
            InlineKeyboardButton("🤷‍♀️ Просто смотрю, что тут", callback_data="first_need_explore"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu with core features"""
    keyboard = [
        [
            InlineKeyboardButton("😱 Паника!", callback_data="panic"),
            InlineKeyboardButton("🕵️‍♀️ Разбор полетов", callback_data="analysis_start"),
        ],
        [
            InlineKeyboardButton("🏆 Дневник побед", callback_data="diary_of_wins"),
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
            InlineKeyboardButton("✨ Да, сделай картинку!", callback_data="create_card_minimalist"),
        ],
        [
            InlineKeyboardButton("🙈 Нет, спасибо", callback_data="skip_card"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_premium_card_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for offering premium card templates."""
    keyboard = [
        [
            InlineKeyboardButton("Минимализм", callback_data="create_card_minimalist"),
            InlineKeyboardButton("✨ Градиент", callback_data="create_card_gradient"),
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


def get_journal_keyboard() -> InlineKeyboardMarkup:
    """Journal mode keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✍️ Продолжить писать", callback_data="journal_continue"),
        ],
        [
            InlineKeyboardButton("✅ Достаточно на сегодня", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wins_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for the Diary of Wins feature."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить победу", callback_data="add_win"),
        ],
        [
            InlineKeyboardButton("« Назад в меню", callback_data="back_to_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm deletion keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("❌ Да, удалить всё", callback_data="confirm_delete"),
        ],
        [
            InlineKeyboardButton("« Отмена", callback_data="settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
