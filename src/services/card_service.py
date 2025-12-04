"""
Service for generating "Insight Cards" from text.
Uses Pillow to create images.
"""
import os
import uuid
import textwrap
from PIL import Image, ImageDraw, ImageFont
from src.config import settings

class CardService:
    """
    Handles the creation of insight card images.
    """

    def __init__(self, generated_cards_path: str = "generated_cards", font_path: str = "assets/fonts/Montserrat-Regular.ttf"):
        """
        Initializes the service and ensures necessary directories and fonts exist.
        """
        self.output_path = generated_cards_path
        self.font_path = font_path
        self.font_bold_path = "assets/fonts/Montserrat-Bold.ttf" # Assuming bold exists for watermark
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            
        # Check if font exists
        if not os.path.exists(self.font_path):
            # In a real scenario, you might want to download it or have a fallback.
            # For now, we'll raise an error or rely on a default.
            # Pillow can sometimes find a default font, but it's not reliable.
            # Let's assume the file is there as per the setup steps.
            pass

    def generate_insight_card(self, insight_text: str, template: str = "minimalist") -> str | None:
        """
        Generates an image card with the given insight text.

        Args:
            insight_text: The text to be written on the card.
            template: The visual template to use (currently only 'minimalist').

        Returns:
            The file path of the generated card, or None if an error occurred.
        """
        try:
            # Card dimensions (stories format)
            width, height = 1080, 1920
            
            if template == "gradient":
                # Premium gradient background
                start_color = (230, 220, 255) # Light lavender
                end_color = (255, 220, 240) # Soft pink
                image = Image.new("RGB", (width, height), start_color)
                draw = ImageDraw.Draw(image)
                for i in range(height):
                    r = start_color[0] + (end_color[0] - start_color[0]) * i // height
                    g = start_color[1] + (end_color[1] - start_color[1]) * i // height
                    b = start_color[2] + (end_color[2] - start_color[2]) * i // height
                    draw.line([(0, i), (width, i)], fill=(r, g, b))
            else: # minimalist
                background_color = (250, 245, 240)  # Pastel off-white/beige
                image = Image.new("RGB", (width, height), background_color)

            draw = ImageDraw.Draw(image)

            # Font settings
            try:
                main_font = ImageFont.truetype(self.font_path, size=70)
                watermark_font = ImageFont.truetype(self.font_path, size=40)
            except IOError:
                # Fallback if font is not found
                main_font = ImageFont.load_default()
                watermark_font = ImageFont.load_default()

            # Text wrapping
            avg_char_width = 40  # Approximate average character width for the font size
            max_chars_per_line = (width - 150) // avg_char_width
            wrapped_text = textwrap.fill(insight_text, width=max_chars_per_line)

            # Text position
            text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=main_font, align="center")
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (width - text_width) / 2
            y = (height - text_height) / 2 - 100 # Position slightly above center

            # Draw the main text
            draw.multiline_text((x, y), wrapped_text, font=main_font, fill=(20, 20, 20), align="center")

            # Watermark
            watermark_text = "AI Friends"
            watermark_bbox = draw.textbbox((0,0), watermark_text, font=watermark_font)
            watermark_width = watermark_bbox[2] - watermark_bbox[0]
            watermark_x = (width - watermark_width) / 2
            watermark_y = height - 150 # Position at the bottom

            draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(150, 150, 150))

            # Save the image
            filename = f"card_{uuid.uuid4()}.png"
            file_path = os.path.join(self.output_path, filename)
            image.save(file_path)

            return file_path

        except Exception as e:
            import logging
            logging.error(f"Error generating insight card: {e}")
            return None
            