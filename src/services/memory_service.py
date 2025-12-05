"""
Service for managing long-term memory using ChromaDB.
"""
import chromadb
import uuid
import logging

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