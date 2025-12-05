"""
Service for transcribing voice messages using OpenAI Whisper API.
"""
import logging
import tempfile
import os
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Handles transcription of audio files using OpenAI Whisper API.
    Uses OpenAI directly (not OpenRouter) as Whisper is not available via OpenRouter.
    """

    def __init__(self, api_key: str):
        """
        Initialize the transcription service.

        Args:
            api_key: OpenAI API key for Whisper API access
        """
        self.client = AsyncOpenAI(api_key=api_key)

    async def transcribe_audio(self, audio_file_path: str, language: str = "ru") -> str:
        """
        Transcribe an audio file to text.

        Args:
            audio_file_path: Path to the audio file (ogg, mp3, wav, etc.)
            language: Language code for transcription (default: Russian)

        Returns:
            Transcribed text or empty string on error
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text",
                )

            return transcription.strip() if transcription else ""

        except Exception as e:
            logger.error(f"Error transcribing audio: {type(e).__name__}: {e}")
            return ""

    async def transcribe_telegram_voice(self, bot, voice_file_id: str) -> str:
        """
        Download and transcribe a Telegram voice message.

        Args:
            bot: Telegram Bot instance for downloading files
            voice_file_id: Telegram file ID of the voice message

        Returns:
            Transcribed text or empty string on error
        """
        temp_file_path = None
        try:
            # Download voice file from Telegram
            voice_file = await bot.get_file(voice_file_id)

            # Create temp file for the audio
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file_path = temp_file.name

            # Download the file
            await voice_file.download_to_drive(temp_file_path)

            # Transcribe
            transcription = await self.transcribe_audio(temp_file_path)

            return transcription

        except Exception as e:
            logger.error(f"Error processing Telegram voice message: {type(e).__name__}: {e}")
            return ""

        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    logger.warning(f"Could not remove temp file {temp_file_path}: {e}")
