"""
Service for managing long-term memory using ChromaDB.
"""
import chromadb
import uuid
from openai import OpenAI
from src.config import settings

class MemoryService:
    """
    Handles storing and retrieving memories from a ChromaDB vector store.
    """

    def __init__(self, chroma_db_path: str):
        """
        Initializes the ChromaDB client and the embedding model.
        """
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        self.openai_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.embedding_model = "text-embedding-ada-002"  # A common choice, available on OpenRouter

    def _get_or_create_collection(self, user_id: int) -> chromadb.Collection:
        """
        Gets or creates a ChromaDB collection for a specific user.
        """
        collection_name = f"user_{user_id}_memories"
        return self.client.get_or_create_collection(name=collection_name)

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

        collection = self._get_or_create_collection(user_id)
        
        # Generate embedding
        response = self.openai_client.embeddings.create(
            input=[text],
            model=self.embedding_model
        )
        embedding = response.data[0].embedding

        # Add to collection
        collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
            ids=[str(uuid.uuid4())]
        )

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
        collection = self._get_or_create_collection(user_id)
        
        # Check if collection is empty
        if collection.count() == 0:
            return []

        # Generate embedding for the query
        response = self.openai_client.embeddings.create(
            input=[query_text],
            model=self.embedding_model
        )
        query_embedding = response.data[0].embedding

        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()), # Ensure n_results is not greater than the number of items
        )

        return results['documents'][0] if results['documents'] else []