"""
Memory Service for RAG-based long-term memory
Uses ChromaDB for vector storage and retrieval
"""
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing long-term memory with ChromaDB"""

    def __init__(self, chroma_db_path: str = "./chroma_db"):
        """
        Initialize ChromaDB client

        Args:
            chroma_db_path: Path to ChromaDB persistent storage
        """
        self.client = chromadb.Client(Settings(
            persist_directory=chroma_db_path,
            anonymized_telemetry=False,
        ))

        # Create or get collection for user memories
        self.collection = self.client.get_or_create_collection(
            name="user_memories",
            metadata={"description": "Long-term memories for AI Friends users"}
        )

        logger.info(f"MemoryService initialized with {self.collection.count()} memories")

    async def save_memory(
        self,
        user_id: int,
        content: str,
        memory_type: str = "general",
        importance: int = 5,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Save a memory to vector database

        Args:
            user_id: User's telegram ID
            content: Memory content/text
            memory_type: Type (entity, emotion, event, insight, etc.)
            importance: 1-10 scale
            metadata: Additional metadata (names, dates, etc.)

        Returns:
            Memory ID
        """
        try:
            memory_id = str(uuid.uuid4())

            # Prepare metadata
            memory_metadata = {
                "user_id": str(user_id),
                "memory_type": memory_type,
                "importance": importance,
                "created_at": datetime.utcnow().isoformat(),
            }

            if metadata:
                memory_metadata.update(metadata)

            # Add to ChromaDB
            self.collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[memory_metadata],
            )

            logger.info(f"Saved memory {memory_id} for user {user_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return ""

    async def recall_memories(
        self,
        user_id: int,
        query: str,
        n_results: int = 5,
        min_importance: int = 3,
    ) -> List[Dict]:
        """
        Recall relevant memories based on query

        Args:
            user_id: User's telegram ID
            query: Query text to find relevant memories
            n_results: Number of results to return
            min_importance: Minimum importance threshold

        Returns:
            List of relevant memories with content and metadata
        """
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results * 2,  # Get more, filter later
                where={"user_id": str(user_id)},
            )

            if not results["documents"] or not results["documents"][0]:
                return []

            # Format and filter results
            memories = []
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]

                # Filter by importance
                if metadata.get("importance", 0) < min_importance:
                    continue

                memories.append({
                    "content": doc,
                    "type": metadata.get("memory_type", "general"),
                    "importance": metadata.get("importance", 5),
                    "created_at": metadata.get("created_at", ""),
                    "distance": results["distances"][0][i] if "distances" in results else None,
                })

            # Sort by importance and distance
            memories.sort(key=lambda x: (-x["importance"], x["distance"] or 0))

            return memories[:n_results]

        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return []

    async def delete_user_memories(self, user_id: int) -> bool:
        """
        Delete all memories for a user

        Args:
            user_id: User's telegram ID

        Returns:
            True if successful
        """
        try:
            # Get all memory IDs for user
            results = self.collection.get(
                where={"user_id": str(user_id)},
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} memories for user {user_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False

    def get_memory_count(self, user_id: int) -> int:
        """Get total number of memories for a user"""
        try:
            results = self.collection.get(
                where={"user_id": str(user_id)},
            )
            return len(results["ids"])
        except Exception as e:
            logger.error(f"Error counting memories: {e}")
            return 0

    async def extract_and_save_from_conversation(
        self,
        user_id: int,
        conversation: List[Dict[str, str]],
        ai_service,
    ) -> List[str]:
        """
        Extract entities/memories from conversation and save them

        Args:
            user_id: User's telegram ID
            conversation: List of messages [{"role": "user/assistant", "content": "..."}]
            ai_service: AIService instance for extraction

        Returns:
            List of memory IDs created
        """
        try:
            # Combine conversation into text
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation[-10:]  # Last 10 messages
            ])

            # Extract entities using AI
            entities = await ai_service.extract_entities(conversation_text)

            memory_ids = []

            # Save names as memories
            for name in entities.get("names", []):
                if name:
                    memory_id = await self.save_memory(
                        user_id=user_id,
                        content=f"Человек в жизни пользователя: {name}",
                        memory_type="entity_person",
                        importance=7,
                        metadata={"name": name},
                    )
                    if memory_id:
                        memory_ids.append(memory_id)

            # Save emotions
            for emotion in entities.get("emotions", []):
                if emotion:
                    memory_id = await self.save_memory(
                        user_id=user_id,
                        content=f"Испытывала чувство: {emotion}",
                        memory_type="emotion",
                        importance=6,
                    )
                    if memory_id:
                        memory_ids.append(memory_id)

            # Save topics
            for topic in entities.get("topics", []):
                if topic:
                    memory_id = await self.save_memory(
                        user_id=user_id,
                        content=f"Обсуждала тему: {topic}",
                        memory_type="topic",
                        importance=5,
                    )
                    if memory_id:
                        memory_ids.append(memory_id)

            # Save summary as main memory
            if entities.get("summary"):
                memory_id = await self.save_memory(
                    user_id=user_id,
                    content=entities["summary"],
                    memory_type="conversation_summary",
                    importance=8,
                )
                if memory_id:
                    memory_ids.append(memory_id)

            logger.info(f"Extracted and saved {len(memory_ids)} memories for user {user_id}")
            return memory_ids

        except Exception as e:
            logger.error(f"Error extracting memories from conversation: {e}")
            return []

    def format_memories_for_context(self, memories: List[Dict]) -> str:
        """
        Format recalled memories for inclusion in AI context

        Args:
            memories: List of memory dicts from recall_memories()

        Returns:
            Formatted string for AI context
        """
        if not memories:
            return ""

        context_parts = ["Из прошлых разговоров я помню:"]

        for memory in memories:
            content = memory["content"]
            context_parts.append(f"- {content}")

        return "\n".join(context_parts)
