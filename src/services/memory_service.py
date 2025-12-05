"""
Service for managing long-term memory using ChromaDB.
Supports:
- Storing conversation summaries
- Entity extraction (names, emotions, topics)
- Semantic search for contextual recall
"""
import chromadb
import uuid
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Handles storing and retrieving memories from a ChromaDB vector store.
    Uses ChromaDB's built-in embedding function to avoid external API dependencies.
    """

    def __init__(self, chroma_db_path: str):
        """
        Initializes the ChromaDB client with default embedding function.
        """
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        # Use ChromaDB's default embedding function (all-MiniLM-L6-v2)
        # This runs locally and doesn't require external API calls
        self.embedding_function = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()

    def _get_or_create_collection(self, user_id: int) -> chromadb.Collection:
        """
        Gets or creates a ChromaDB collection for a specific user.
        """
        collection_name = f"user_{user_id}_memories"
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

    def add_memory(self, user_id: int, text: str, metadata: dict = None):
        """
        Adds a piece of text to the user's long-term memory.

        Args:
            user_id: The ID of the user.
            text: The text to remember.
            metadata: Optional metadata to store with the memory.
        """
        if not text:
            return

        try:
            collection = self._get_or_create_collection(user_id)

            # ChromaDB will generate embeddings automatically using the default function
            collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[str(uuid.uuid4())]
            )
        except Exception as e:
            # Log error but don't crash - memory is a nice-to-have feature
            logger.warning(f"Failed to add memory for user {user_id}: {e}")

    def search_memories(self, user_id: int, query_text: str, n_results: int = 5) -> list[str]:
        """
        Searches for relevant memories for a user based on a query.

        Args:
            user_id: The ID of the user.
            query_text: The text to search for.
            n_results: The maximum number of results to return.

        Returns:
            A list of the most relevant memory texts.
        """
        try:
            collection = self._get_or_create_collection(user_id)

            # Check if collection is empty
            if collection.count() == 0:
                return []

            # Query the collection - ChromaDB handles embedding automatically
            results = collection.query(
                query_texts=[query_text],
                n_results=min(n_results, collection.count()),
            )

            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            # Log error but return empty list - search is a nice-to-have feature
            logger.warning(f"Failed to search memories for user {user_id}: {e}")
            return []

    def add_conversation_memory(
        self,
        user_id: int,
        conversation_summary: str,
        entities: Dict[str, any] = None,
        conversation_type: str = "general",
        importance: int = 5
    ):
        """
        Add a conversation summary with extracted entities to memory.

        Args:
            user_id: User ID
            conversation_summary: Summary of the conversation
            entities: Extracted entities (names, emotions, topics)
            conversation_type: Type of conversation (panic, analysis, journal)
            importance: Importance score 1-10
        """
        metadata = {
            "type": "conversation",
            "conversation_type": conversation_type,
            "importance": importance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if entities:
            # Store entities as JSON string in metadata
            if entities.get("names"):
                metadata["names"] = json.dumps(entities["names"], ensure_ascii=False)
            if entities.get("emotions"):
                metadata["emotions"] = json.dumps(entities["emotions"], ensure_ascii=False)
            if entities.get("topics"):
                metadata["topics"] = json.dumps(entities["topics"], ensure_ascii=False)

        self.add_memory(user_id, conversation_summary, metadata)

    def add_entity_memory(
        self,
        user_id: int,
        entity_name: str,
        entity_type: str,
        context: str,
        importance: int = 5
    ):
        """
        Add a specific entity (person, topic) to memory.

        Args:
            user_id: User ID
            entity_name: Name of the entity (e.g., "Саша", "работа")
            entity_type: Type (person, topic, place, emotion)
            context: Context about this entity
            importance: Importance score 1-10
        """
        text = f"{entity_name}: {context}"
        metadata = {
            "type": "entity",
            "entity_type": entity_type,
            "entity_name": entity_name,
            "importance": importance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.add_memory(user_id, text, metadata)

    def search_by_entity(
        self,
        user_id: int,
        entity_name: str,
        n_results: int = 5
    ) -> List[str]:
        """
        Search memories related to a specific entity (person, topic).

        Args:
            user_id: User ID
            entity_name: Name to search for
            n_results: Max results

        Returns:
            List of relevant memory texts
        """
        # Search using the entity name as query
        return self.search_memories(user_id, entity_name, n_results)

    def get_context_for_conversation(
        self,
        user_id: int,
        current_message: str,
        n_results: int = 3
    ) -> Optional[str]:
        """
        Get relevant context from past conversations for AI prompt.

        Args:
            user_id: User ID
            current_message: Current user message
            n_results: Number of memories to retrieve

        Returns:
            Formatted context string or None
        """
        memories = self.search_memories(user_id, current_message, n_results)

        if not memories:
            return None

        # Format memories into context
        context_parts = []
        for memory in memories:
            # Truncate long memories
            if len(memory) > 200:
                memory = memory[:200] + "..."
            context_parts.append(f"• {memory}")

        return "Из прошлых разговоров:\n" + "\n".join(context_parts)

    def get_recent_topics(self, user_id: int, limit: int = 5) -> List[str]:
        """
        Get recent topics discussed with the user.

        Args:
            user_id: User ID
            limit: Max topics to return

        Returns:
            List of topic strings
        """
        try:
            collection = self._get_or_create_collection(user_id)

            if collection.count() == 0:
                return []

            # Get all memories and extract topics from metadata
            results = collection.get(
                limit=min(limit * 3, collection.count()),  # Get more to filter
                include=["metadatas"]
            )

            topics = []
            for metadata in results.get("metadatas", []):
                if metadata and metadata.get("topics"):
                    try:
                        topic_list = json.loads(metadata["topics"])
                        topics.extend(topic_list)
                    except json.JSONDecodeError:
                        pass

            # Return unique topics
            return list(set(topics))[:limit]

        except Exception as e:
            logger.warning(f"Failed to get recent topics for user {user_id}: {e}")
            return []

    def clear_user_memories(self, user_id: int):
        """
        Delete all memories for a user.

        Args:
            user_id: User ID
        """
        try:
            collection_name = f"user_{user_id}_memories"
            self.client.delete_collection(collection_name)
            logger.info(f"Cleared all memories for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to clear memories for user {user_id}: {e}")