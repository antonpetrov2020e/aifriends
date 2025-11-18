"""
Gratitude service for Gratitude Journal (Phase 3)
Helps users track what they're grateful for
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database.models import User, GratitudeEntry, MoodEntry
from .ai_service import AIService


class GratitudeService:
    """Service for managing gratitude journal and mood tracking"""

    def __init__(self, db_session: Session):
        """
        Initialize GratitudeService

        Args:
            db_session: SQLAlchemy session
        """
        self.db = db_session

    def save_gratitude(
        self,
        user: User,
        content: str,
        tags: Optional[str] = None
    ) -> GratitudeEntry:
        """
        Save gratitude entry

        Args:
            user: User object
            content: Gratitude text
            tags: Optional comma-separated tags

        Returns:
            GratitudeEntry object
        """
        entry = GratitudeEntry(
            user_id=user.id,
            content=content,
            tags=tags
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    def get_today_gratitude(self, user: User) -> Optional[GratitudeEntry]:
        """
        Get today's gratitude entry

        Args:
            user: User object

        Returns:
            GratitudeEntry if exists today
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        return self.db.query(GratitudeEntry).filter(
            GratitudeEntry.user_id == user.id,
            GratitudeEntry.created_at >= today_start
        ).first()

    def get_week_gratitudes(self, user: User) -> List[GratitudeEntry]:
        """
        Get gratitude entries for the last 7 days

        Args:
            user: User object

        Returns:
            List of GratitudeEntry objects
        """
        week_ago = datetime.utcnow() - timedelta(days=7)

        return self.db.query(GratitudeEntry).filter(
            GratitudeEntry.user_id == user.id,
            GratitudeEntry.created_at >= week_ago
        ).order_by(GratitudeEntry.created_at.desc()).all()

    def get_all_gratitudes(self, user: User, limit: int = 50) -> List[GratitudeEntry]:
        """
        Get all gratitude entries

        Args:
            user: User object
            limit: Maximum number of entries

        Returns:
            List of GratitudeEntry objects
        """
        return self.db.query(GratitudeEntry).filter(
            GratitudeEntry.user_id == user.id
        ).order_by(GratitudeEntry.created_at.desc()).limit(limit).all()

    def get_gratitude_count(self, user: User) -> int:
        """
        Get total number of gratitude entries

        Args:
            user: User object

        Returns:
            Count of entries
        """
        return self.db.query(GratitudeEntry).filter(
            GratitudeEntry.user_id == user.id
        ).count()

    async def generate_week_summary(
        self,
        user: User,
        ai_service: AIService
    ) -> str:
        """
        Generate AI summary of the week's gratitudes

        Args:
            user: User object
            ai_service: AIService for generating summary

        Returns:
            Summary text
        """
        gratitudes = self.get_week_gratitudes(user)

        if not gratitudes:
            return "На этой неделе ты еще не записывала благодарности 🌸"

        # Prepare gratitudes text
        gratitudes_text = "\n".join([
            f"- {entry.content}" for entry in gratitudes
        ])

        # Generate AI summary
        prompt = f"""На основе этих записей благодарности за неделю, создай краткое (2-3 предложения) тёплое резюме:

{gratitudes_text}

Задача: Заметить паттерны, что важно для этого человека, за что он благодарен чаще всего. Использовать Tone of Voice "подружки" - заботливо, без формальности."""

        summary = await ai_service.chat(
            user_message=prompt,
            conversation_history=[],
            context="Создаешь резюме недели благодарности"
        )

        return summary

    # Mood tracking methods

    def save_mood(
        self,
        user: User,
        mood: int,  # 1, 2, or 3
        note: Optional[str] = None
    ) -> MoodEntry:
        """
        Save mood entry

        Args:
            user: User object
            mood: 1 (😔), 2 (😐), 3 (😊)
            note: Optional note about the mood

        Returns:
            MoodEntry object
        """
        entry = MoodEntry(
            user_id=user.id,
            mood=mood,
            note=note
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    def get_week_moods(self, user: User) -> List[MoodEntry]:
        """
        Get mood entries for the last 7 days

        Args:
            user: User object

        Returns:
            List of MoodEntry objects
        """
        week_ago = datetime.utcnow() - timedelta(days=7)

        return self.db.query(MoodEntry).filter(
            MoodEntry.user_id == user.id,
            MoodEntry.created_at >= week_ago
        ).order_by(MoodEntry.created_at.asc()).all()

    def get_average_mood(self, user: User, days: int = 7) -> float:
        """
        Calculate average mood for the last N days

        Args:
            user: User object
            days: Number of days to calculate

        Returns:
            Average mood (1.0 - 3.0)
        """
        days_ago = datetime.utcnow() - timedelta(days=days)

        result = self.db.query(func.avg(MoodEntry.mood)).filter(
            MoodEntry.user_id == user.id,
            MoodEntry.created_at >= days_ago
        ).scalar()

        return float(result) if result else 2.0  # Default to neutral

    def format_mood_graph(self, moods: List[MoodEntry]) -> str:
        """
        Format mood entries as a simple text graph

        Args:
            moods: List of MoodEntry objects

        Returns:
            Text representation of mood graph
        """
        if not moods:
            return "Нет данных о настроении за эту неделю"

        mood_emojis = {1: "😔", 2: "😐", 3: "😊"}

        graph_lines = []
        for entry in moods:
            date_str = entry.created_at.strftime("%d.%m")
            emoji = mood_emojis.get(entry.mood, "❓")
            graph_lines.append(f"{date_str}: {emoji}")

        return "\n".join(graph_lines)

    async def generate_mood_insights(
        self,
        user: User,
        ai_service: AIService
    ) -> str:
        """
        Generate AI insights about mood patterns

        Args:
            user: User object
            ai_service: AIService for generating insights

        Returns:
            Insights text
        """
        moods = self.get_week_moods(user)

        if len(moods) < 3:
            return "Пока недостаточно данных для анализа настроения. Отмечай настроение чаще! 📊"

        # Count mood distribution
        mood_counts = {1: 0, 2: 0, 3: 0}
        for entry in moods:
            mood_counts[entry.mood] += 1

        # Prepare mood data for AI
        mood_text = f"""Статистика настроения за неделю:
- Хорошо (😊): {mood_counts[3]} дней
- Нормально (😐): {mood_counts[2]} дней
- Плохо (😔): {mood_counts[1]} дней

Записи по дням:
{self.format_mood_graph(moods)}
"""

        prompt = f"""На основе этих данных о настроении, дай краткий (2-3 предложения) инсайт:

{mood_text}

Задача: Заметить паттерны (если есть), дать поддержку, мотивировать продолжать отслеживать. Использовать Tone of Voice "подружки"."""

        insights = await ai_service.chat(
            user_message=prompt,
            conversation_history=[],
            context="Создаешь инсайт о настроении пользователя"
        )

        return insights
