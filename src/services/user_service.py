"""
User service for managing user data and consent
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

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
        user.consent_date = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def complete_onboarding(self, user: User) -> User:
        """Mark onboarding as completed"""
        user.onboarding_completed = True
        self.db.commit()
        self.db.refresh(user)
        return user

    def check_analysis_limit(self, user: User, free_limit: int = 3) -> tuple[bool, int]:
        """
        Check if user can perform another analysis
        Returns (can_analyze, remaining_count)
        """
        # Premium users have unlimited access
        if user.is_premium:
            return True, -1  # -1 means unlimited

        # Check if week has passed since last reset
        week_ago = datetime.utcnow() - timedelta(days=7)
        if user.last_analysis_reset < week_ago:
            # Reset counter
            user.analyses_this_week = 0
            user.last_analysis_reset = datetime.utcnow()
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
            print(f"Error deleting user history: {e}")
            return False

    def is_premium(self, user: User) -> bool:
        """Check if user has active premium subscription"""
        if not user.is_premium:
            return False

        if user.premium_until and user.premium_until < datetime.utcnow():
            # Premium expired
            user.is_premium = False
            self.db.commit()
            return False

        return True
