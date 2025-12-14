# ============================================================================
# Test Configuration & Fixtures
# ============================================================================
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import Base, get_db
from app.config import get_settings

# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

test_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with test_session_maker() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client"""
    client = MagicMock()
    client.send_text = AsyncMock(return_value={"messages": [{"id": "test_msg_id"}]})
    client.send_buttons = AsyncMock(return_value={"messages": [{"id": "test_msg_id"}]})
    client.send_list = AsyncMock(return_value={"messages": [{"id": "test_msg_id"}]})
    client.mark_as_read = AsyncMock()
    return client

@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine"""
    engine = MagicMock()
    engine.query = AsyncMock(return_value=(
        "This is a test response from the RAG engine.",
        [{"content": "Test context", "score": 0.9}]
    ))
    engine.generate_practice_question = AsyncMock(return_value={
        "question": "What is 2 + 2?",
        "question_type": "short_answer",
        "correct_answer": "4",
        "explanation": "Basic addition"
    })
    return engine

@pytest.fixture
def sample_student_data():
    """Sample student data for tests"""
    return {
        "first_name": "Tatenda",
        "last_name": "Moyo",
        "education_level": "secondary",
        "grade": "Form 3",
        "school_name": "Test High School",
        "subjects": ["Mathematics", "Physics"],
        "preferred_language": "english"
    }

@pytest.fixture
def sample_question_data():
    """Sample question data for tests"""
    return {
        "question_text": "What is the formula for the area of a circle?",
        "question_type": "short_answer",
        "correct_answer": "πr²",
        "marking_scheme": "Award 1 mark for correct formula",
        "marks": 1,
        "difficulty": "easy"
    }