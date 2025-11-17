"""
Database models for AI Friends bot
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)

    # Consent and onboarding
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(String(50), default="start")  # Track current onboarding step
    tour_completed = Column(Boolean, default=False)  # Whether user completed interactive tour

    # Premium status
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)

    # Usage tracking (for freemium limits)
    analyses_this_week = Column(Integer, default=0)
    last_analysis_reset = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation/dialogue session model"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Conversation type
    conversation_type = Column(String(50), nullable=False)  # panic, analysis, journal, etc.

    # State management
    current_state = Column(String(50), nullable=True)  # for multi-step dialogues
    context_data = Column(Text, nullable=True)  # JSON-encoded context

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual message in a conversation"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Metadata
    message_type = Column(String(50), nullable=True)  # text, button_click, insight, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    """Extracted memories for RAG (Phase 2)"""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Memory content
    content = Column(Text, nullable=False)
    memory_type = Column(String(50), nullable=True)  # entity, emotion, event, etc.

    # For vector search (Phase 2)
    embedding_id = Column(String(255), nullable=True)  # ID in ChromaDB

    # Importance/relevance (for prioritization)
    importance = Column(Integer, default=5)  # 1-10 scale

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="memories")


class InsightCard(Base):
    """Generated shareable insight cards (Phase 3)"""

    __tablename__ = "insight_cards"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Card content
    insight_text = Column(Text, nullable=False)
    image_url = Column(String(512), nullable=True)
    template_type = Column(String(50), default="minimalist")

    # Virality tracking
    shared = Column(Boolean, default=False)
    shared_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(database_url: str):
    """Initialize database"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
