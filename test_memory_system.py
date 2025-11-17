"""
Test script for RAG Memory System
Tests the MemoryService functionality
"""
import asyncio
import logging
from src.config import settings
from src.database import init_db, get_session
from src.database.models import User
from src.services.memory_service import MemoryService
from src.services.ai_service import AIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_memory_system():
    """Test the memory system"""

    print("=" * 60)
    print("Testing RAG Memory System")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")
    engine = init_db(settings.database_url)
    db_session = get_session(engine)

    # Initialize services
    print("2. Initializing AI service...")
    ai_service = AIService(
        api_key=settings.openrouter_api_key,
        model=settings.llm_model,
    )

    print("3. Initializing Memory service...")
    memory_service = MemoryService(
        db_session=db_session,
        chroma_db_path=settings.chroma_db_path,
    )

    # Create test user
    print("\n4. Creating test user...")
    test_user = User(
        telegram_id=12345,
        username="test_user",
        first_name="Test",
        consent_given=True,
        onboarding_completed=True,
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    print(f"   Created user: {test_user.id}")

    # Test 1: Store memories
    print("\n5. Testing memory storage...")

    memory1 = memory_service.store_memory(
        user=test_user,
        content="Переживала из-за ссоры с Алексом. Он не писал два дня.",
        memory_type="summary",
        importance=8,
        metadata={"names": ["Алекс"], "emotions": ["тревога", "обида"]}
    )
    print(f"   ✓ Stored memory 1: {memory1.content[:50]}...")

    memory2 = memory_service.store_memory(
        user=test_user,
        content="Испытывала тревогу из-за работы. Боялась не справиться с проектом.",
        memory_type="summary",
        importance=7,
        metadata={"emotions": ["тревога", "страх"], "topics": ["работа", "проект"]}
    )
    print(f"   ✓ Stored memory 2: {memory2.content[:50]}...")

    memory3 = memory_service.store_memory(
        user=test_user,
        content="Упоминался человек: Алекс",
        memory_type="entity",
        importance=9,
        metadata={"entity_name": "Алекс"}
    )
    print(f"   ✓ Stored memory 3: {memory3.content}")

    # Test 2: Search memories
    print("\n6. Testing memory search...")

    # Search for "Алекс"
    query1 = "Алекс опять молчит"
    results1 = memory_service.search_memories(test_user, query1, top_k=3)
    print(f"\n   Query: '{query1}'")
    print(f"   Found {len(results1)} memories:")
    for mem, score in results1:
        print(f"     - [{score:.3f}] {mem.content[:60]}...")

    # Search for "работа"
    query2 = "Боюсь что на работе не получится"
    results2 = memory_service.search_memories(test_user, query2, top_k=3)
    print(f"\n   Query: '{query2}'")
    print(f"   Found {len(results2)} memories:")
    for mem, score in results2:
        print(f"     - [{score:.3f}] {mem.content[:60]}...")

    # Test 3: Get context for query
    print("\n7. Testing context generation...")
    context = memory_service.get_context_for_query(test_user, query1)
    print(f"   Generated context:\n{context}")

    # Test 4: Memory stats
    print("\n8. Getting memory stats...")
    stats = memory_service.get_memory_stats(test_user)
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   Most accessed: {stats['most_accessed']['content'][:50]}...")

    # Cleanup
    print("\n9. Cleanup...")
    memory_service.delete_user_memories(test_user)
    db_session.delete(test_user)
    db_session.commit()
    print("   ✓ Cleaned up test data")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_memory_system())
