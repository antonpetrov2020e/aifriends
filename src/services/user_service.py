"""
User service for managing user data and consent
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
import logging

from ..database.models import User


class UserService:
    """Service for user management"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_or_create_user(self, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> User:
        """Get existing user or create new one"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        return user

    def give_consent(self, user: User) -> User:
        """Mark user as having given consent"""
        user.consent_given = True
        user.consent_date = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def complete_onboarding(self, user: User) -> User:
        """Mark onboarding as completed"""
        user.onboarding_completed = True
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_preferred_name(self, user: User, preferred_name: str) -> User:
        """Set user's preferred name"""
        user.preferred_name = preferred_name
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_display_name(self, user: User) -> str:
        """Get user's display name (preferred_name or fallback to first_name)"""
        return user.preferred_name or user.first_name or "друг"

    def check_analysis_limit(self, user: User, free_limit: int = 3) -> tuple[bool, int]:
        """
        Check if user can perform another analysis
        Returns (can_analyze, remaining_count)
        """
        # Premium users have unlimited access
        if user.is_premium:
            return True, -1  # -1 means unlimited

        # Check if week has passed since last reset
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        if user.last_analysis_reset < week_ago:
            # Reset counter
            user.analyses_this_week = 0
            user.last_analysis_reset = datetime.now(timezone.utc)
            self.db.commit()

        remaining = free_limit - user.analyses_this_week
        can_analyze = remaining > 0

        return can_analyze, remaining

    def increment_analysis_count(self, user: User) -> User:
        """Increment analysis counter for free users"""
        if not user.is_premium:
            user.analyses_this_week += 1
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete_user_history(self, user: User) -> bool:
        """Delete all user data (for privacy compliance)"""
        try:
            # This will cascade delete all related records
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logging.error(f"Error deleting user history: {e}")
            return False

    def delete_user_data(self, user: User) -> bool:
        """Delete user's conversations and memories, but keep the account"""
        try:
            # Delete all conversations (cascades to messages)
            for conversation in user.conversations:
                self.db.delete(conversation)

            # Delete all memories
            for memory in user.memories:
                self.db.delete(memory)

            # Reset usage counters
            user.analyses_this_week = 0
            user.last_analysis_reset = datetime.now(timezone.utc)

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logging.error(f"Error deleting user data: {e}")
            return False

    def is_premium(self, user: User) -> bool:
        """Check if user has active premium subscription"""
        if not user.is_premium:
            return False

        if user.premium_until:
            # Handle both naive and aware datetimes
            premium_until = user.premium_until
            now = datetime.now(timezone.utc)

            # If premium_until is naive, assume it's UTC
            if premium_until.tzinfo is None:
                premium_until = premium_until.replace(tzinfo=timezone.utc)

            if premium_until < now:
                # Premium expired
                user.is_premium = False
                self.db.commit()
                return False

        return True

    def grant_premium(self, user: User, days: int) -> User:
        """Grant premium access to a user for a number of days."""
        user.is_premium = True
        user.premium_until = datetime.now(timezone.utc) + timedelta(days=days)
        self.db.commit()
        self.db.refresh(user)
        return user

    def add_win(self, user: User, content: str):
        """Adds a 'win' to the user's diary."""
        from ..database.models import Win
        new_win = Win(user_id=user.id, content=content)
        self.db.add(new_win)
        self.db.commit()
        return new_win

    def get_wins(self, user: User) -> list:
        """Retrieves all 'wins' for a user."""
        from ..database.models import Win
        return self.db.query(Win).filter(Win.user_id == user.id).order_by(Win.created_at.desc()).all()
