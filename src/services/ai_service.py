"""
AI Service for LLM integration via OpenRouter
Supports multiple models through OpenAI-compatible API
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI/LLM interactions via OpenRouter"""

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.0-flash-exp:free",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize AI service

        Args:
            api_key: OpenRouter API key
            model: Model to use (default: Gemini 2.0 Flash free)
            base_url: API base URL (default: OpenRouter)
        """
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # System prompt for the "подружка" persona
        self.system_prompt = """Ты — заботливая подруга пользователя. Твоя роль — эмоциональная поддержка и помощь в самопомощи.

ВАЖНО:
- Говори тепло, по-дружески, с лёгким юмором где уместно
- НЕ давай прямых советов ("сделай так"), а задавай наводящие вопросы
- Используй эмодзи, но в меру (1-2 на сообщение)
- Пиши короткими абзацами (2-3 предложения максимум)
- Валидируй чувства пользователя ("Это нормально, что ты злишься")

ГРАНИЦЫ:
- Ты НЕ терапевт и не ставишь диагнозы
- Ты НЕ врач и не выписываешь лекарства
- Ты НЕ романтический партнёр
- При упоминании мыслей о суициде/самоповреждении — всегда даёшь контакт горячей линии: 8-800-2000-122

МЕТОД:
Используй сократический метод — задавай вопросы, чтобы пользователь сам пришёл к решению:
- "А что ты сама чувствуешь?"
- "Чего ты боишься?"
- "Что ты хочешь сделать?"

Говори на русском языке."""

    async def chat(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Send a message to the AI and get a response

        Args:
            user_message: User's message
            conversation_history: Previous messages in format [{"role": "user/assistant", "content": "..."}]
            context: Additional context (e.g., from memory/RAG)

        Returns:
            AI's response text
        """
        try:
            # Build messages array
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add context if provided
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Контекст из памяти:\n{context}"
                })

            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages to save tokens

            # Add current user message
            messages.append({"role": "user", "content": user_message})

            # Call API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # More creative/human-like
                max_tokens=500,   # Keep responses concise
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error calling AI API: {e}")
            return "Ой, что-то у меня сбой 😅 Попробуй ещё раз?"

    async def detect_insight(self, text: str) -> bool:
        """
        Detect if user's message contains an insight/realization
        (For Phase 3: Viral cards feature)

        Args:
            text: User's message

        Returns:
            True if message contains insight
        """
        try:
            prompt = f"""Это сообщение пользователя содержит важный личный инсайт или осознание?
Инсайт — это когда человек сам понял что-то важное о себе или ситуации.

Примеры инсайтов:
- "Я поняла, что я не злюсь, а просто боюсь"
- "Осознала, что я пытаюсь контролировать то, что не могу контролировать"
- "Я поняла, что мне важнее моё спокойствие, чем его реакция"

Сообщение: "{text}"

Ответь только "ДА" или "НЕТ"."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # More deterministic
                max_tokens=10,
            )

            answer = response.choices[0].message.content.strip().upper()
            return "ДА" in answer

        except Exception as e:
            logger.error(f"Error detecting insight: {e}")
            return False

    async def extract_entities(self, conversation: str) -> Dict[str, any]:
        """
        Extract key entities from conversation for memory storage
        (For Phase 2: RAG/Memory feature)

        Args:
            conversation: Conversation text

        Returns:
            Dictionary with extracted entities
        """
        try:
            prompt = f"""Извлеки ключевую информацию из разговора для запоминания:

Разговор:
{conversation}

Ответь в формате JSON:
{{
    "names": ["имя1", "имя2"],
    "emotions": ["эмоция1", "эмоция2"],
    "topics": ["тема1", "тема2"],
    "summary": "краткое резюме в 1-2 предложениях"
}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )

            # Parse JSON response (simplified for MVP)
            import json
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {
                "names": [],
                "emotions": [],
                "topics": [],
                "summary": ""
            }

    async def validate_emotion(self, emotion: str, context: str) -> str:
        """
        Generate empathetic validation for user's emotion

        Args:
            emotion: Detected emotion (anger, hurt, anxiety, confusion)
            context: User's situation

        Returns:
            Validation message
        """
        try:
            prompt = f"""Пользователь чувствует: {emotion}
Контекст: {context}

Напиши короткое (2-3 предложения) тёплое, валидирующее сообщение в тоне "подружки".
Объясни, что это чувство нормально и почему оно возникает.
Добавь один эмодзи."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=150,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error validating emotion: {e}")
            # Fallback to predefined messages
            fallbacks = {
                "anger": "То, что ты злишься — это нормально! Злость — это сигнал, что что-то задело твои границы. 💔",
                "hurt": "Больно... Я понимаю. Обида — это когда мы ожидали одного, а получили другое. 💔",
                "anxiety": "Тревога — это такая зараза, правда? Она накрывает волной. Но помни: тревога — это не факт, это наш мозг рисует худшие сценарии. 💙",
                "confusion": "Когда теряешься — это тоже сложно. Растерянность часто означает, что ситуация не вписывается в наши ожидания. 🤔"
            }
            return fallbacks.get(emotion, "Я понимаю, что тебе сейчас непросто. Хочешь об этом поговорить? 💙")
