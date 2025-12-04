"""
Integration tests for BotHandlers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, CallbackQuery, Message, Chat

# Setup paths for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bot.handlers import BotHandlers
from src.services.user_service import UserService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, User

# Use an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Fixture to create a new database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_services():
    """Fixture to create mock services."""
    return {
        "ai_service": AsyncMock(),
        "memory_service": AsyncMock(),
        "card_service": AsyncMock(),
        "payment_service": MagicMock(),
    }

@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

@pytest.fixture
def bot_handlers(db_session, mock_services):
    """Fixture to create a BotHandlers instance."""
    return BotHandlers(
        db_session=db_session,
        ai_service=mock_services["ai_service"],
        memory_service=mock_services["memory_service"],
        card_service=mock_services["card_service"],
        payment_service=mock_services["payment_service"],
        free_analysis_limit=3,
    )

@pytest.fixture
def telegram_user():
    """A mock telegram user."""
    return TelegramUser(id=12345, first_name="Test", is_bot=False, username="testuser")

@pytest.fixture
def mock_update():
    """Fixture for a mock telegram Update object."""
    update = MagicMock(spec=Update)
    update.effective_user = TelegramUser(id=12345, first_name="Test", is_bot=False)
    update.callback_query = AsyncMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.message = AsyncMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Fixture for a mock telegram Context object."""
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_diary_of_wins_non_premium(bot_handlers, user_service, telegram_user, mock_update, mock_context):
    """Test that non-premium users are shown a premium-only message."""
    # Arrange
    user = user_service.get_or_create_user(telegram_id=telegram_user.id)
    user.is_premium = False
    
    mock_update.effective_user = telegram_user
    mock_update.callback_query.data = "diary_of_wins"
    
    # Act
    await bot_handlers.wins_callback(mock_update, mock_context)
    
    # Assert
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
    assert "это премиум-функция" in call_args

@pytest.mark.asyncio
async def test_diary_of_wins_premium_empty(bot_handlers, user_service, telegram_user, mock_update, mock_context):
    """Test that premium users with no wins see the empty state message."""
    # Arrange
    user = user_service.get_or_create_user(telegram_id=telegram_user.id)
    user_service.grant_premium(user, days=30)
    
    mock_update.effective_user = telegram_user
    mock_update.callback_query.data = "diary_of_wins"

    # Act
    await bot_handlers.wins_callback(mock_update, mock_context)

    # Assert
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
    assert "Твой Дневник побед пока пуст" in call_args

@pytest.mark.asyncio
async def test_add_win_flow(bot_handlers, user_service, telegram_user, mock_update, mock_context):
    """Test the flow for adding a new win."""
    # Arrange: User is premium
    user = user_service.get_or_create_user(telegram_id=telegram_user.id)
    user_service.grant_premium(user, days=30)
    
    # 1. User clicks "Add win"
    mock_update.effective_user = telegram_user
    mock_update.callback_query.data = "add_win"
    
    # Act
    await bot_handlers.wins_callback(mock_update, mock_context)
    
    # Assert: bot asks for the win text
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        "Какая у тебя сегодня победа? Это может быть что угодно, от 'вышла на пробежку' до 'закрыла большой проект'.\n\nНапиши ее 👇",
        parse_mode='HTML'
    )
    assert mock_context.user_data["conversation_mode"] == "adding_win"

    # 2. User sends the win text
    win_text = "I completed all my tests!"
    mock_update.message = MagicMock(spec=Message)
    mock_update.message.text = win_text
    
    # Act
    await bot_handlers.handle_text_message(mock_update, mock_context)

    # Assert: win is saved and confirmation is sent
    wins = user_service.get_wins(user)
    assert len(wins) == 1
    assert wins[0].content == win_text
    
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "победа записана" in call_args
    assert "conversation_mode" not in mock_context.user_data

@pytest.mark.asyncio
async def test_payment_flow(bot_handlers, user_service, telegram_user, mock_update, mock_context, mock_services):
    """Test the full payment initiation and confirmation flow."""
    # Arrange
    user = user_service.get_or_create_user(telegram_id=telegram_user.id)
    mock_update.effective_user = telegram_user

    # 1. User clicks "premium"
    mock_update.callback_query.data = "premium"
    mock_payment = MagicMock()
    mock_payment.id = "payment_xyz"
    mock_payment.confirmation.confirmation_url = "http://pay.url"
    mock_services["payment_service"].create_payment.return_value = mock_payment
    
    # Act
    await bot_handlers.settings_callback(mock_update, mock_context)

    # Assert: bot sends payment link
    mock_services["payment_service"].create_payment.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args
    assert "Оплатить" in str(call_args)
    assert mock_context.user_data["pending_payment_id"] == "payment_xyz"

    # 2. User clicks "I have paid"
    mock_update.callback_query.data = "check_payment"
    
    # Mock the payment status check to return success
    succeeded_payment = MagicMock()
    succeeded_payment.status = "succeeded"
    mock_services["payment_service"].check_payment_status.return_value = succeeded_payment
    
    # Act
    await bot_handlers.check_payment_callback(mock_update, mock_context)

    # Assert: user is granted premium
    db_user = user_service.get_or_create_user(telegram_id=telegram_user.id)
    assert user_service.is_premium(db_user) is True
    
    # Check confirmation message
    final_call_args = mock_update.callback_query.edit_message_text.call_args[0][0]
    assert "Оплата прошла успешно" in final_call_args
    assert "pending_payment_id" not in mock_context.user_data
