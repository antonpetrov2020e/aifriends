"""
Tests for the PaymentService.
"""
import pytest
from unittest.mock import Mock, patch
from src.services.payment_service import PaymentService

@pytest.fixture
def payment_service():
    """Fixture to create a PaymentService instance for testing."""
    return PaymentService(shop_id="test_shop_id", secret_key="test_secret_key")

def test_initialization_failure():
    """Test that PaymentService raises an error if credentials are not provided."""
    with pytest.raises(ValueError):
        PaymentService(shop_id="", secret_key="")
    with pytest.raises(ValueError):
        PaymentService(shop_id="123", secret_key="")
    with pytest.raises(ValueError):
        PaymentService(shop_id="", secret_key="abc")


@patch('src.services.payment_service.Payment')
def test_create_payment(mock_payment_class, payment_service):
    """Test the creation of a payment."""
    mock_payment = Mock()
    mock_payment.confirmation.confirmation_url = "https://example.com/pay"
    mock_payment_class.create.return_value = mock_payment

    user_id = 123
    amount = 990.0
    description = "Test subscription"
    
    payment = payment_service.create_payment(user_id=user_id, amount=amount, description=description)

    assert payment is not None
    assert payment.confirmation.confirmation_url == "https://example.com/pay"

    # Check that yookassa.Payment.create was called correctly
    mock_payment_class.create.assert_called_once()
    args, kwargs = mock_payment_class.create.call_args
    payment_data = args[0]
    
    assert payment_data["amount"]["value"] == f"{amount:.2f}"
    assert payment_data["amount"]["currency"] == "RUB"
    assert payment_data["description"] == description
    assert payment_data["metadata"]["user_id"] == user_id


@patch('src.services.payment_service.Payment')
def test_check_payment_status(mock_payment_class, payment_service):
    """Test checking the status of a payment."""
    mock_payment = Mock()
    mock_payment.status = "succeeded"
    mock_payment_class.find_one.return_value = mock_payment

    payment_id = "payment_123"
    status = payment_service.check_payment_status(payment_id)

    assert status is not None
    assert status.status == "succeeded"
    mock_payment_class.find_one.assert_called_once_with(payment_id)


@patch('src.services.payment_service.Payment')
def test_create_payment_api_error(mock_payment_class, payment_service):
    """Test that create_payment handles API errors."""
    mock_payment_class.create.side_effect = Exception("API connection error")

    payment = payment_service.create_payment(user_id=1, amount=100.0, description="Test")
    
    assert payment is None
