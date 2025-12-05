"""
Database models for AI Friends bot
"""
from datetime import datetime, timezone
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
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

class Base(DeclarativeBase):
    pass


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    preferred_name = Column(String(255), nullable=True)  # User's chosen name

    # Consent and onboarding
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed = Column(Boolean, default=False)

    # Premium status
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime(timezone=True), nullable=True)

    # Usage tracking (for freemium limits)
    analyses_this_week = Column(Integer, default=0)
    last_analysis_reset = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Notification settings
    notifications_enabled = Column(Boolean, default=False)
    notification_morning_time = Column(String(5), default="09:00")  # HH:MM format
    notification_evening_time = Column(String(5), default="21:00")  # HH:MM format

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    wins = relationship("Win", back_populates="user", cascade="all, delete-orphan")


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
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
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
    shared_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Win(Base):
    """'Diary of Wins' entry model (Phase 3)"""

    __tablename__ = "wins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="wins")


def init_db(database_url: str):
    """Initialize database with automatic migration support"""
    engine = create_engine(database_url)

    # Create all tables
    Base.metadata.create_all(engine)

    # Run migrations for existing databases
    _migrate_add_preferred_name(engine)
    _migrate_add_notification_fields(engine)

    return engine


def _migrate_add_preferred_name(engine):
    """Migration: Add preferred_name column to users table if missing"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    # Check if users table exists
    if 'users' not in inspector.get_table_names():
        return  # Table doesn't exist yet, will be created by create_all

    # Check if preferred_name column exists
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'preferred_name' not in columns:
        # Add the column using raw SQL (SQLite doesn't support ALTER TABLE through SQLAlchemy easily)
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN preferred_name VARCHAR(255)"))
                conn.commit()
                print("✅ Migration: Added 'preferred_name' column to users table")
            except Exception as e:
                print(f"⚠️  Migration warning: {e}")
                # Column might already exist, ignore


def _migrate_add_notification_fields(engine):
    """Migration: Add notification columns to users table if missing"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)

    # Check if users table exists
    if 'users' not in inspector.get_table_names():
        return

    columns = [col['name'] for col in inspector.get_columns('users')]

    migrations = [
        ("notifications_enabled", "ALTER TABLE users ADD COLUMN notifications_enabled BOOLEAN DEFAULT 0"),
        ("notification_morning_time", "ALTER TABLE users ADD COLUMN notification_morning_time VARCHAR(5) DEFAULT '09:00'"),
        ("notification_evening_time", "ALTER TABLE users ADD COLUMN notification_evening_time VARCHAR(5) DEFAULT '21:00'"),
    ]

    with engine.connect() as conn:
        for column_name, sql in migrations:
            if column_name not in columns:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Migration: Added '{column_name}' column to users table")
                except Exception as e:
                    print(f"⚠️  Migration warning for {column_name}: {e}")


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
