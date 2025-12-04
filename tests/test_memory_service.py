"""
Tests for the MemoryService.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.services.memory_service import MemoryService

@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client."""
    with patch('src.services.memory_service.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3] # Dummy embedding
        mock_data = MagicMock()
        mock_data.data = [mock_embedding]
        mock_client.embeddings.create.return_value = mock_data
        mock_openai.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_chromadb_client():
    """Fixture to mock the ChromaDB client."""
    with patch('src.services.memory_service.chromadb.PersistentClient') as mock_chroma:
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        # Mock the collection's methods
        mock_collection.add = MagicMock()
        mock_collection.query = MagicMock()
        mock_collection.count.return_value = 1 # Default to non-empty

        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client
        yield mock_client

@pytest.fixture
def memory_service(mock_openai_client, mock_chromadb_client):
    """Fixture to create a MemoryService instance with mocked clients."""
    # We need to ensure the service is initialized *after* the patches are active
    return MemoryService(chroma_db_path="/tmp/fake_path")

def test_add_memory(memory_service):
    """Test adding a memory to a user's collection."""
    user_id = 123
    text = "Test memory"
    metadata = {"source": "test"}

    memory_service.add_memory(user_id, text, metadata)

    mock_collection = memory_service.client.get_or_create_collection()
    
    # Check that collection.add was called
    mock_collection.add.assert_called_once()
    args, kwargs = mock_collection.add.call_args
    
    assert kwargs['documents'] == [text]
    assert kwargs['metadatas'] == [metadata]
    assert kwargs['embeddings'][0] == [0.1, 0.2, 0.3]

def test_search_memories(memory_service):
    """Test searching for memories."""
    user_id = 456
    query_text = "What was the test memory?"
    
    # Configure the mock query result
    mock_collection = memory_service.client.get_or_create_collection()
    mock_collection.query.return_value = {
        'documents': [['retrieved memory 1', 'retrieved memory 2']]
    }
    mock_collection.count.return_value = 5 # Ensure count is > n_results

    results = memory_service.search_memories(user_id, query_text, n_results=2)

    assert results == ['retrieved memory 1', 'retrieved memory 2']
    mock_collection.query.assert_called_once()
    args, kwargs = mock_collection.query.call_args
    assert kwargs['n_results'] == 2
    assert kwargs['query_embeddings'][0] == [0.1, 0.2, 0.3]

def test_search_in_empty_collection(memory_service):
    """Test that searching in an empty collection returns an empty list."""
    user_id = 789
    query_text = "Search query"

    mock_collection = memory_service.client.get_or_create_collection()
    mock_collection.count.return_value = 0 # Simulate empty collection
    mock_collection.query.reset_mock() # Reset from previous tests

    results = memory_service.search_memories(user_id, query_text)

    assert results == []
    # Ensure query is not called if the collection is empty
    mock_collection.query.assert_not_called()

def test_add_memory_with_no_text(memory_service):
    """Test that add_memory does nothing if the text is empty."""
    user_id = 101

    mock_collection = memory_service.client.get_or_create_collection()
    mock_collection.add.reset_mock()

    memory_service.add_memory(user_id, "")

    mock_collection.add.assert_not_called()
