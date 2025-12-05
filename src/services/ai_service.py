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
        self.system_prompt = """Ты — заботливая подруга пользователя. Твоя роль — эмоциональная поддержка через активное слушание и помощь в самопомощи.

ПРИНЦИПЫ АКТИВНОГО СЛУШАНИЯ (по методике Карла Роджерса):
- ОТРАЖАЙ чувства: "Похоже, ты чувствуешь..." / "Я слышу, что тебе..."
- ПЕРЕФРАЗИРУЙ суть: покажи, что ты ПОНЯЛА, о чем она говорит
- ВАЛИДИРУЙ эмоции: "Это абсолютно нормально чувствовать..." / "На твоем месте я бы тоже..."
- ПРОЯВЛЯЙ ЭМПАТИЮ: представь себя на ее месте, почувствуй ситуацию
- НЕ СПЕШИ с вопросами: сначала покажи, что слышишь и понимаешь

СТРУКТУРА ОТВЕТА:
1. Эмоциональное отражение (что она чувствует)
2. Суть ситуации своими словами (показать, что поняла)
3. Валидация чувств (это нормально)
4. Мягкий наводящий вопрос (если уместно)

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:
❌ "Слышу тебя. А что ты почувствовала?" (слишком формально)
✅ "Ого, как же это обидно, когда самые близкие обесценивают то, что для тебя важно... Мама хотела как лучше, но ее слова про 'игрушки' и 'трату времени' прям задели за живое, да? И теперь эта радость от рисования куда-то испарилась, потому что в голове крутится 'а может, я правда ерундой занимаюсь?'

На твоем месте я бы тоже сомневалась. Когда мнение близкого человека расходится с тем, что приносит тебе счастье, это внутренний разрыв — выбирать между 'делать маме приятное' и 'делать себе приятное'.

А скажи, до этого разговора — когда ты рисовала — что именно тебе давало этот 'заряд энергии'? Это что-то про творчество, про результат, про признание?'"

СТИЛЬ:
- Говори тепло, искренне, по-человечески
- Используй "..." для передачи раздумий
- Эмодзи 1-2 на сообщение, где уместно
- Короткие абзацы (2-4 предложения)
- НЕ используй шаблонные фразы типа "слышу тебя"

ГРАНИЦЫ:
- Ты НЕ терапевт и не ставишь диагнозы
- Ты НЕ врач и не выписываешь лекарства
- Ты НЕ романтический партнёр
- При упоминании мыслей о суициде/самоповреждении — всегда даёшь контакт горячей линии: 8-800-2000-122

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
            logger.error(f"Error calling AI API: {type(e).__name__}: {e}")
            logger.error(f"User message: {user_message[:100]}")
            logger.error(f"Model: {self.model}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
            logger.error(f"Error extracting entities: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "names": [],
                "emotions": [],
                "topics": [],
                "summary": ""
            }

    async def empathetic_first_response(self, user_story: str) -> str:
        """
        Generate deep empathetic response using active listening technique
        This is for the first response to user's situation description

        Args:
            user_story: User's detailed situation description

        Returns:
            Empathetic response with active listening
        """
        try:
            prompt = f"""Пользователь только что поделился своей ситуацией. Это твой ПЕРВЫЙ ответ на его историю.

ИСТОРИЯ ПОЛЬЗОВАТЕЛЯ:
{user_story}

ЗАДАЧА:
Примени технику АКТИВНОГО СЛУШАНИЯ (Карл Роджерс):
1. Отрази чувства, которые ты услышала
2. Перефрази суть ситуации своими словами (покажи, что поняла)
3. Валидируй эмоции (это нормально чувствовать так)
4. Задай ОДИН мягкий наводящий вопрос для углубления

ВАЖНО:
- НЕ используй шаблоны типа "Слышу тебя" или "Я понимаю"
- Будь конкретной к ЭТОЙ истории
- Покажи, что ты ПРОЧУВСТВОВАЛА ситуацию
- Пиши 3-5 предложений

Напиши эмпатичный ответ:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=400,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error in empathetic_first_response: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback - better than "Слышу тебя"
            return "Ого, как же это непросто... Я вижу, что это действительно задело тебя. Расскажи, что ты почувствовала в тот момент?"

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
            logger.error(f"Error validating emotion: {type(e).__name__}: {e}")
            logger.error(f"Emotion: {emotion}, Context: {context[:100] if context else 'None'}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to predefined messages
            fallbacks = {
                "anger": "То, что ты злишься — это нормально! Злость — это сигнал, что что-то задело твои границы. 💔",
                "hurt": "Больно... Я понимаю. Обида — это когда мы ожидали одного, а получили другое. 💔",
                "anxiety": "Тревога — это такая зараза, правда? Она накрывает волной. Но помни: тревога — это не факт, это наш мозг рисует худшие сценарии. 💙",
                "confusion": "Когда теряешься — это тоже сложно. Растерянность часто означает, что ситуация не вписывается в наши ожидания. 🤔"
            }
            return fallbacks.get(emotion, "Я понимаю, что тебе сейчас непросто. Хочешь об этом поговорить? 💙")

    async def thinking_dialogue(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Generate a Socratic dialogue response to help user think through their situation
        Uses open-ended questions to guide self-discovery

        Args:
            user_message: User's message
            conversation_history: Previous messages
            context: Additional context (memories, situation)

        Returns:
            Socratic response with guiding question
        """
        try:
            socratic_prompt = """Ты ведёшь сократический диалог с пользователем.

ЗАДАЧА: Помоги пользователю САМОСТОЯТЕЛЬНО прийти к осознаниям через наводящие вопросы.

ПРАВИЛА:
1. НЕ давай советов и готовых ответов
2. Задавай ОДИН открытый вопрос за раз
3. Отражай то, что услышала (1 предложение)
4. Вопрос должен быть направлен на:
   - Истинные желания ("Чего ты НА САМОМ ДЕЛЕ хочешь?")
   - Страхи под поверхностью ("Что самое страшное может случиться?")
   - Личные границы ("Что для тебя НЕ приемлемо?")
   - Ценности ("Что для тебя важнее всего здесь?")

ФОРМАТ:
- Короткое отражение (1 предложение)
- Один наводящий вопрос

Пример:
"Похоже, ты разрываешься между желанием угодить маме и своими интересами... А если бы мамы не было рядом — чего бы ТЫ хотела в этой ситуации?"
"""

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "system", "content": socratic_prompt}
            ]

            if context:
                messages.append({
                    "role": "system",
                    "content": f"Контекст:\n{context}"
                })

            if conversation_history:
                messages.extend(conversation_history[-10:])

            messages.append({"role": "user", "content": user_message})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=300,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error in thinking_dialogue: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "Это интересно... А что ты сама думаешь об этом?"
