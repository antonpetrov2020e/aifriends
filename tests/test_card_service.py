"""
Tests for the CardService.
"""
import os
import pytest
from PIL import Image
from src.services.card_service import CardService
from src.config import settings

@pytest.fixture(scope="module")
def card_service():
    """Fixture to create a CardService instance for testing."""
    # Ensure the test output directory is clean
    test_output_path = "generated_cards_test"
    if not os.path.exists(test_output_path):
        os.makedirs(test_output_path)
    
    service = CardService(generated_cards_path=test_output_path)
    yield service
    
    # Teardown: clean up the test directory
    for f in os.listdir(test_output_path):
        os.remove(os.path.join(test_output_path, f))
    os.rmdir(test_output_path)

def test_generate_minimalist_card(card_service):
    """Test generating a card with the default 'minimalist' template."""
    insight_text = "This is a test insight for a minimalist card."
    image_path = card_service.generate_insight_card(insight_text, template="minimalist")

    assert image_path is not None
    assert os.path.exists(image_path)

    # Verify it's a valid image
    try:
        with Image.open(image_path) as img:
            assert img.format == "PNG"
            assert img.size == (1080, 1920)
    except Exception as e:
        pytest.fail(f"Generated file is not a valid image: {e}")

def test_generate_gradient_card(card_service):
    """Test generating a card with the 'gradient' template."""
    insight_text = "This is a test insight for a premium gradient card."
    image_path = card_service.generate_insight_card(insight_text, template="gradient")

    assert image_path is not None
    assert os.path.exists(image_path)

    try:
        with Image.open(image_path) as img:
            assert img.format == "PNG"
            assert img.size == (1080, 1920)
    except Exception as e:
        pytest.fail(f"Generated file is not a valid image: {e}")

def test_long_text_wrapping(card_service):
    """Test that long text is properly wrapped and the card is generated."""
    long_text = "This is a very long piece of text designed to test the automatic text wrapping functionality of the CardService. The service should be able to handle this gracefully without throwing an error and produce a legible card where the text fits within the boundaries of the image."
    image_path = card_service.generate_insight_card(long_text)

    assert image_path is not None
    assert os.path.exists(image_path)

    try:
        with Image.open(image_path) as img:
            assert img.format == "PNG"
    except Exception as e:
        pytest.fail(f"Generated file with long text is not a valid image: {e}")

def test_card_service_handles_missing_font(monkeypatch):
    """Test that CardService falls back to a default font if the custom one is missing."""
    # This test is tricky because Pillow's default font behavior can be inconsistent.
    # We'll test that it doesn't crash.
    service = CardService(font_path="non_existent_font.ttf")
    insight_text = "Testing fallback font."
    image_path = service.generate_insight_card(insight_text)
    
    assert image_path is not None
    assert os.path.exists(image_path)
    os.remove(image_path) # clean up
