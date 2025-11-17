"""
Memory service for RAG (Retrieval Augmented Generation) system
Implements long-term memory using ChromaDB and embeddings
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from ..database.models import Memory, User, Conversation, Message

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for managing user memories using RAG

    Features:
    - Store conversation summaries as memories
    - Search for relevant memories using semantic similarity
    - Extract entities and key information from conversations
    - Provide context for AI responses
    """

    def __init__(
        self,
        db_session: Session,
        chroma_db_path: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        """
        Initialize memory service

        Args:
            db_session: SQLAlchemy database session
            chroma_db_path: Path to ChromaDB storage
            embedding_model: Name of sentence-transformers model (multilingual for Russian support)
        """
        self.db = db_session

        # Initialize embedding model (multilingual for Russian)
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # Initialize ChromaDB
        logger.info(f"Initializing ChromaDB at: {chroma_db_path}")
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # Get or create collection for memories
        self.collection = self.chroma_client.get_or_create_collection(
            name="user_memories",
            metadata={"description": "Long-term memory storage for AI Friends bot"}
        )

        logger.info("MemoryService initialized successfully")

    def store_memory(
        self,
        user: User,
        content: str,
        memory_type: str = "general",
        importance: int = 5,
        metadata: Optional[Dict] = None,
    ) -> Memory:
        """
        Store a new memory for the user

        Args:
            user: User object
            content: Memory content (summary, entity, etc.)
            memory_type: Type of memory (entity, emotion, event, etc.)
            importance: Importance score (1-10)
            metadata: Additional metadata (names, emotions, topics, etc.)

        Returns:
            Memory object
        """
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content, convert_to_tensor=False)

            # Create unique ID for this memory
            memory_id = f"user_{user.id}_memory_{datetime.utcnow().timestamp()}"

            # Prepare metadata for ChromaDB
            chroma_metadata = {
                "user_id": user.id,
                "memory_type": memory_type,
                "importance": importance,
                "created_at": datetime.utcnow().isoformat(),
            }
            if metadata:
                chroma_metadata.update(metadata)

            # Store in ChromaDB
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[content],
                metadatas=[chroma_metadata],
                ids=[memory_id],
            )

            # Store in SQL database
            memory = Memory(
                user_id=user.id,
                content=content,
                memory_type=memory_type,
                embedding_id=memory_id,
                importance=importance,
            )
            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)

            logger.info(f"Stored memory for user {user.id}: {content[:50]}...")
            return memory

        except Exception as e:
            logger.error(f"Error storing memory: {type(e).__name__}: {e}")
            self.db.rollback()
            raise

    def search_memories(
        self,
        user: User,
        query: str,
        top_k: int = 3,
        min_importance: int = 3,
    ) -> List[Tuple[Memory, float]]:
        """
        Search for relevant memories using semantic similarity

        Args:
            user: User object
            query: Search query (current user message)
            top_k: Number of top results to return
            min_importance: Minimum importance score to consider

        Returns:
            List of tuples (Memory, similarity_score)
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=False)

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k * 2,  # Get more results to filter by user
                where={"user_id": user.id},
            )

            if not results["ids"][0]:
                logger.info(f"No memories found for user {user.id}")
                return []

            # Get Memory objects from database and calculate scores
            memories_with_scores = []
            for i, memory_id in enumerate(results["ids"][0]):
                # Get memory from database
                memory = self.db.query(Memory).filter(
                    Memory.embedding_id == memory_id,
                    Memory.importance >= min_importance,
                ).first()

                if memory:
                    # Distance from ChromaDB (lower is better, convert to similarity)
                    distance = results["distances"][0][i]
                    similarity_score = 1 / (1 + distance)  # Convert distance to similarity

                    # Update access count
                    memory.access_count += 1
                    memory.last_accessed = datetime.utcnow()

                    memories_with_scores.append((memory, similarity_score))

            self.db.commit()

            # Sort by similarity and return top_k
            memories_with_scores.sort(key=lambda x: x[1], reverse=True)
            result = memories_with_scores[:top_k]

            logger.info(f"Found {len(result)} relevant memories for user {user.id}")
            return result

        except Exception as e:
            logger.error(f"Error searching memories: {type(e).__name__}: {e}")
            return []

    def get_context_for_query(
        self,
        user: User,
        query: str,
        max_tokens: int = 500,
    ) -> str:
        """
        Get formatted memory context for AI query

        Args:
            user: User object
            query: Current user message
            max_tokens: Maximum tokens for context (rough estimate)

        Returns:
            Formatted context string
        """
        memories = self.search_memories(user, query, top_k=5)

        if not memories:
            return ""

        # Format context
        context_parts = []
        total_length = 0

        for memory, score in memories:
            # Only include if similarity is high enough
            if score < 0.3:
                continue

            memory_text = f"- {memory.content}"
            memory_length = len(memory_text.split())

            # Check if we're within token limit (rough estimate: 1 token ≈ 1 word)
            if total_length + memory_length > max_tokens:
                break

            context_parts.append(memory_text)
            total_length += memory_length

        if context_parts:
            context = "Что я помню о тебе:\n" + "\n".join(context_parts)
            logger.info(f"Generated context for user {user.id}: {len(context_parts)} memories")
            return context

        return ""

    def extract_and_store_from_conversation(
        self,
        user: User,
        conversation: Conversation,
        ai_service,
    ) -> List[Memory]:
        """
        Extract key information from conversation and store as memories

        Args:
            user: User object
            conversation: Conversation object
            ai_service: AIService instance for entity extraction

        Returns:
            List of created Memory objects
        """
        try:
            # Get all messages from conversation
            messages = self.db.query(Message).filter(
                Message.conversation_id == conversation.id
            ).order_by(Message.created_at).all()

            if not messages:
                logger.info(f"No messages in conversation {conversation.id}")
                return []

            # Format conversation for extraction
            conversation_text = "\n".join([
                f"{'Пользователь' if msg.role == 'user' else 'Помощник'}: {msg.content}"
                for msg in messages
            ])

            # Extract entities using AI
            import asyncio
            entities = asyncio.run(ai_service.extract_entities(conversation_text))

            memories = []

            # Store summary as main memory
            if entities.get("summary"):
                memory = self.store_memory(
                    user=user,
                    content=entities["summary"],
                    memory_type="summary",
                    importance=7,
                    metadata={
                        "conversation_id": conversation.id,
                        "conversation_type": conversation.conversation_type,
                    }
                )
                memories.append(memory)

            # Store names/entities
            for name in entities.get("names", []):
                memory = self.store_memory(
                    user=user,
                    content=f"Упоминался человек: {name}",
                    memory_type="entity",
                    importance=8,  # Names are very important
                    metadata={
                        "entity_name": name,
                        "conversation_id": conversation.id,
                    }
                )
                memories.append(memory)

            # Store emotions as context
            if entities.get("emotions"):
                emotions_text = f"Испытывала: {', '.join(entities['emotions'])}"
                memory = self.store_memory(
                    user=user,
                    content=emotions_text,
                    memory_type="emotion",
                    importance=6,
                    metadata={
                        "emotions": entities["emotions"],
                        "conversation_id": conversation.id,
                    }
                )
                memories.append(memory)

            # Store topics
            if entities.get("topics"):
                topics_text = f"Обсуждали: {', '.join(entities['topics'])}"
                memory = self.store_memory(
                    user=user,
                    content=topics_text,
                    memory_type="topic",
                    importance=5,
                    metadata={
                        "topics": entities["topics"],
                        "conversation_id": conversation.id,
                    }
                )
                memories.append(memory)

            logger.info(f"Extracted and stored {len(memories)} memories from conversation {conversation.id}")
            return memories

        except Exception as e:
            logger.error(f"Error extracting memories from conversation: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def delete_user_memories(self, user: User) -> bool:
        """
        Delete all memories for a user (for privacy compliance)

        Args:
            user: User object

        Returns:
            True if successful
        """
        try:
            # Get all memory IDs for this user
            memories = self.db.query(Memory).filter(Memory.user_id == user.id).all()
            memory_ids = [m.embedding_id for m in memories if m.embedding_id]

            # Delete from ChromaDB
            if memory_ids:
                self.collection.delete(ids=memory_ids)

            # Delete from SQL (will cascade with user deletion)
            for memory in memories:
                self.db.delete(memory)

            self.db.commit()

            logger.info(f"Deleted {len(memories)} memories for user {user.id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting user memories: {type(e).__name__}: {e}")
            self.db.rollback()
            return False

    def get_memory_stats(self, user: User) -> Dict:
        """
        Get statistics about user's memories

        Args:
            user: User object

        Returns:
            Dictionary with memory statistics
        """
        memories = self.db.query(Memory).filter(Memory.user_id == user.id).all()

        if not memories:
            return {
                "total_memories": 0,
                "by_type": {},
                "most_accessed": None,
            }

        # Count by type
        by_type = {}
        for memory in memories:
            by_type[memory.memory_type] = by_type.get(memory.memory_type, 0) + 1

        # Get most accessed
        most_accessed = max(memories, key=lambda m: m.access_count)

        return {
            "total_memories": len(memories),
            "by_type": by_type,
            "most_accessed": {
                "content": most_accessed.content[:100],
                "access_count": most_accessed.access_count,
                "type": most_accessed.memory_type,
            }
        }
