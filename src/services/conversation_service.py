"""
Conversation service for managing conversation history and memory
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import json

from ..database.models import User, Conversation, Message


class ConversationService:
    """Service for conversation and message management"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_or_create_conversation(
        self,
        user: User,
        conversation_type: str = "general"
    ) -> Conversation:
        """
        Get active conversation or create new one

        Args:
            user: User object
            conversation_type: Type of conversation (panic, analysis, journal, general)

        Returns:
            Active Conversation object
        """
        # Try to find active (not ended) conversation of this type
        conversation = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user.id,
                Conversation.conversation_type == conversation_type,
                Conversation.ended_at.is_(None)
            )
            .order_by(Conversation.started_at.desc())
            .first()
        )

        if not conversation:
            # Create new conversation
            conversation = Conversation(
                user_id=user.id,
                conversation_type=conversation_type,
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

        return conversation

    def save_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        message_type: Optional[str] = None
    ) -> Message:
        """
        Save message to conversation history

        Args:
            conversation: Conversation object
            role: Message role (user, assistant, system)
            content: Message content
            message_type: Optional message type (text, button_click, etc.)

        Returns:
            Created Message object
        """
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            message_type=message_type or "text",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_conversation_history(
        self,
        conversation: Conversation,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history in format suitable for AI

        Args:
            conversation: Conversation object
            limit: Optional limit on number of messages (default: all)

        Returns:
            List of messages in format [{"role": "user", "content": "..."}]
        """
        query = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
        )

        if limit:
            # Get last N messages
            query = query.limit(limit)

        messages = query.all()
        messages.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    def get_recent_conversations_summary(
        self,
        user: User,
        days: int = 7,
        limit: int = 5
    ) -> str:
        """
        Get summary of recent conversations for context

        Args:
            user: User object
            days: Number of days to look back
            limit: Max number of conversations to include

        Returns:
            Text summary of recent conversations
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        conversations = (
            self.db.query(Conversation)
            .filter(
                Conversation.user_id == user.id,
                Conversation.started_at >= cutoff_date
            )
            .order_by(Conversation.started_at.desc())
            .limit(limit)
            .all()
        )

        if not conversations:
            return ""

        summary_parts = []
        for conv in conversations:
            # Get first few messages to understand context
            messages = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
                .limit(3)
                .all()
            )

            if messages:
                context = " ".join([m.content[:100] for m in messages if m.role == "user"])
                summary_parts.append(f"[{conv.conversation_type}]: {context}...")

        return "\n".join(summary_parts)

    def end_conversation(self, conversation: Conversation) -> Conversation:
        """Mark conversation as ended"""
        conversation.ended_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def update_conversation_state(
        self,
        conversation: Conversation,
        state: str,
        context_data: Optional[Dict] = None
    ) -> Conversation:
        """
        Update conversation state and context data

        Args:
            conversation: Conversation object
            state: Current state (e.g., "waiting_for_feelings")
            context_data: Additional context data to store

        Returns:
            Updated Conversation object
        """
        conversation.current_state = state
        if context_data:
            conversation.context_data = json.dumps(context_data)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation_context(self, conversation: Conversation) -> Optional[Dict]:
        """Get stored context data from conversation"""
        if conversation.context_data:
            try:
                return json.loads(conversation.context_data)
            except json.JSONDecodeError:
                return None
        return None
