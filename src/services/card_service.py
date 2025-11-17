"""
Card Service for generating shareable insight cards
Creates beautiful images with user insights for social sharing
"""
import logging
import os
import textwrap
from io import BytesIO
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)


class CardService:
    """Service for generating insight card images"""

    # Card templates with colors
    TEMPLATES = {
        "minimalist": {
            "bg_color": (255, 245, 240),  # Warm white
            "text_color": (60, 60, 60),    # Dark gray
            "accent_color": (200, 150, 180),  # Soft pink
            "name": "Минимализм"
        },
        "pastel_pink": {
            "bg_color": (255, 228, 225),  # Misty rose
            "text_color": (100, 60, 80),   # Deep mauve
            "accent_color": (255, 192, 203),  # Pink
            "name": "Нежный розовый"
        },
        "calm_blue": {
            "bg_color": (230, 240, 250),  # Light blue
            "text_color": (50, 70, 100),   # Dark blue
            "accent_color": (135, 170, 210),  # Medium blue
            "name": "Спокойный синий"
        },
        "nature_green": {
            "bg_color": (240, 250, 240),  # Mint cream
            "text_color": (60, 90, 60),    # Forest green
            "accent_color": (150, 200, 150),  # Light green
            "name": "Природный зеленый"
        },
    }

    def __init__(self, cards_dir: str = "./generated_cards"):
        """
        Initialize card service

        Args:
            cards_dir: Directory to save generated cards
        """
        self.cards_dir = cards_dir
        os.makedirs(cards_dir, exist_ok=True)

        # Try to load a font, fall back to default if unavailable
        self.font_path = self._find_font()

        logger.info(f"CardService initialized, saving to {cards_dir}")

    def _find_font(self) -> Optional[str]:
        """Find available TTF font on system"""
        # Common font paths on different systems
        font_candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:\\Windows\\Fonts\\arial.ttf",  # Windows
        ]

        for font_path in font_candidates:
            if os.path.exists(font_path):
                logger.info(f"Using font: {font_path}")
                return font_path

        logger.warning("No TTF font found, using PIL default")
        return None

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get font of specified size"""
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size)
            except Exception as e:
                logger.warning(f"Error loading font: {e}")

        # Fallback to default
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within max_width"""
        lines = []

        # Split by existing newlines first
        paragraphs = text.split('\n')

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                lines.append('')
                continue

            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = font.getbbox(test_line)
                width = bbox[2] - bbox[0]

                if width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(' '.join(current_line))

        return lines

    async def generate_insight_card(
        self,
        insight_text: str,
        template: str = "minimalist",
        user_name: Optional[str] = None,
    ) -> Optional[BytesIO]:
        """
        Generate insight card image

        Args:
            insight_text: The insight text to display
            template: Template name (from TEMPLATES)
            user_name: Optional user name for watermark

        Returns:
            BytesIO object containing PNG image, or None on error
        """
        try:
            # Get template colors
            template_config = self.TEMPLATES.get(template, self.TEMPLATES["minimalist"])
            bg_color = template_config["bg_color"]
            text_color = template_config["text_color"]
            accent_color = template_config["accent_color"]

            # Card dimensions (1080x1920 for Instagram Stories)
            width, height = 1080, 1920

            # Create image
            img = Image.new('RGB', (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Add subtle gradient/texture (optional)
            for i in range(height):
                alpha = int(10 * (i / height))
                overlay_color = tuple(max(0, c - alpha) for c in bg_color)
                draw.line([(0, i), (width, i)], fill=overlay_color)

            # Font sizes
            quote_font = self._get_font(60)
            watermark_font = self._get_font(30)

            # Add quote mark or decorative element
            quote_mark = '"'
            quote_bbox = draw.textbbox((0, 0), quote_mark, font=quote_font)
            quote_width = quote_bbox[2] - quote_bbox[0]
            draw.text(
                (80, 400),
                quote_mark,
                font=quote_font,
                fill=accent_color
            )

            # Wrap and center insight text
            max_text_width = width - 160  # 80px margin on each side
            wrapped_lines = self._wrap_text(insight_text, quote_font, max_text_width)

            # Calculate total text height
            line_height = 80
            total_text_height = len(wrapped_lines) * line_height

            # Center vertically
            y_start = (height - total_text_height) // 2

            # Draw each line
            for i, line in enumerate(wrapped_lines):
                bbox = draw.textbbox((0, 0), line, font=quote_font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                y = y_start + (i * line_height)

                draw.text(
                    (x, y),
                    line,
                    font=quote_font,
                    fill=text_color
                )

            # Add watermark at bottom
            watermark = "AI Friends • твоя карманная подружка"
            bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
            wm_width = bbox[2] - bbox[0]
            draw.text(
                ((width - wm_width) // 2, height - 150),
                watermark,
                font=watermark_font,
                fill=accent_color
            )

            # Add decorative line
            line_y = height - 200
            draw.line(
                [(width // 2 - 100, line_y), (width // 2 + 100, line_y)],
                fill=accent_color,
                width=2
            )

            # Save to BytesIO
            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            output.seek(0)

            logger.info(f"Generated insight card with template '{template}'")
            return output

        except Exception as e:
            logger.error(f"Error generating insight card: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_available_templates(self) -> Dict[str, str]:
        """Get list of available templates with names"""
        return {
            key: config["name"]
            for key, config in self.TEMPLATES.items()
        }

    async def save_card_for_user(
        self,
        user_id: int,
        insight_text: str,
        template: str = "minimalist",
    ) -> Optional[str]:
        """
        Generate and save card to file

        Args:
            user_id: User telegram ID
            insight_text: The insight text
            template: Template name

        Returns:
            Path to saved file, or None on error
        """
        try:
            card_io = await self.generate_insight_card(insight_text, template)

            if not card_io:
                return None

            # Save to file
            filename = f"card_{user_id}_{int(datetime.utcnow().timestamp())}.png"
            filepath = os.path.join(self.cards_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(card_io.getvalue())

            logger.info(f"Saved card to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving card: {e}")
            return None
