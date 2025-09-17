"""
Test configuration and fixtures for KubeRAG test suite
"""
import pytest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone
import asyncio

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_text():
    """Sample text for testing"""
    return """
    Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines.
    Machine learning is a subset of AI that enables computers to learn and improve from experience.
    Natural Language Processing (NLP) helps computers understand and interpret human language.
    
    The field of AI has grown rapidly in recent years. Deep learning, a subset of machine learning,
    uses artificial neural networks to model and understand complex patterns in data.
    """

@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        "id": "test_doc_1",
        "content": "This is a test document about artificial intelligence and machine learning.",
        "metadata": {
            "title": "Test Document",
            "author": "Test Author",
            "created": "2024-01-01T00:00:00Z"
        }
    }

@pytest.fixture
def sample_documents():
    """Multiple sample documents for testing"""
    return [
        {
            "id": "doc_1",
            "content": "Machine learning is a subset of artificial intelligence.",
            "metadata": {"source": "book1.pdf"}
        },
        {
            "id": "doc_2", 
            "content": "Deep learning uses neural networks for pattern recognition.",
            "metadata": {"source": "paper1.pdf"}
        },
        {
            "id": "doc_3",
            "content": "Machine learning is a subset of artificial intelligence.",  # Duplicate
            "metadata": {"source": "book2.pdf"}
        }
    ]

@pytest.fixture
def sample_chunks():
    """Sample chunks for testing"""
    return [
        {
            "id": "chunk_1",
            "text": "Machine learning is a subset of artificial intelligence.",
            "metadata": {"doc_id": "doc_1", "chunk_index": 0}
        },
        {
            "id": "chunk_2",
            "text": "Deep learning uses neural networks for pattern recognition.",
            "metadata": {"doc_id": "doc_2", "chunk_index": 0}
        }
    ]

@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing"""
    mock_model = Mock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]] * 5  # 5D embeddings
    mock_model.get_sentence_embedding_dimension.return_value = 5
    return mock_model

@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    mock_store = Mock()
    mock_store.search.return_value = [
        {"id": "chunk_1", "score": 0.9, "text": "Sample text 1"},
        {"id": "chunk_2", "score": 0.8, "text": "Sample text 2"}
    ]
    mock_store.add.return_value = True
    mock_store.delete.return_value = True
    return mock_store

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing"""
    mock_provider = Mock()
    mock_provider.generate_response.return_value = {
        "response": "This is a test response",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }
    return mock_provider

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "vector_store": {
            "type": "qdrant",
            "host": "localhost",
            "port": 6333
        },
        "llm_providers": {
            "openai": {
                "api_key": "test_key",
                "model": "gpt-3.5-turbo"
            }
        },
        "storage": {
            "type": "local",
            "path": "/tmp/test_storage"
        },
        "chunking": {
            "strategy": "recursive_character",
            "chunk_size": 1000,
            "overlap": 200
        }
    }

@pytest.fixture
def sample_lineage_events():
    """Sample lineage events for testing"""
    return [
        {
            "event_id": "event_1",
            "event_type": "document_ingested",
            "timestamp": "2024-01-01T00:00:00Z",
            "source_documents": ["doc_1"],
            "source_chunks": ["chunk_1", "chunk_2"]
        },
        {
            "event_id": "event_2", 
            "event_type": "query_executed",
            "timestamp": "2024-01-01T01:00:00Z",
            "output_content": "What is machine learning?",
            "parameters": {"query_id": "query_1"}
        }
    ]

@pytest.fixture
def sample_cost_records():
    """Sample cost tracking records"""
    return [
        {
            "timestamp": "2024-01-01T00:00:00Z",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "cost": 0.002,
            "tokens_used": 1000,
            "user_id": "user_1"
        },
        {
            "timestamp": "2024-01-01T01:00:00Z",
            "provider": "openai",
            "model": "gpt-4",
            "cost": 0.06,
            "tokens_used": 1000,
            "user_id": "user_2"
        }
    ]

@pytest.fixture
def mock_prometheus_registry():
    """Mock Prometheus registry for testing"""
    from unittest.mock import Mock
    
    mock_registry = Mock()
    mock_counter = Mock()
    mock_histogram = Mock()
    mock_gauge = Mock()
    
    # Mock metric creation
    mock_counter.labels.return_value.inc = Mock()
    mock_histogram.labels.return_value.observe = Mock()
    mock_gauge.labels.return_value.set = Mock()
    
    return {
        "registry": mock_registry,
        "counter": mock_counter,
        "histogram": mock_histogram,
        "gauge": mock_gauge
    }

@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for HTTP tests"""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status = 200
    mock_response.json = Mock(return_value={"status": "healthy"})
    mock_session.get.return_value.__aenter__.return_value = mock_response
    return mock_session

# Test data files
@pytest.fixture
def create_test_files(temp_dir):
    """Create test files in temporary directory"""
    files = {}
    
    # Create a sample text file
    text_file = Path(temp_dir) / "sample.txt"
    text_file.write_text("This is a sample text file for testing.")
    files["text"] = str(text_file)
    
    # Create a sample JSON file
    json_file = Path(temp_dir) / "sample.json"
    json_data = {"title": "Test Document", "content": "Sample JSON content"}
    json_file.write_text(json.dumps(json_data))
    files["json"] = str(json_file)
    
    # Create a sample CSV file
    csv_file = Path(temp_dir) / "sample.csv"
    csv_file.write_text("name,age,city\nJohn,30,New York\nJane,25,London")
    files["csv"] = str(csv_file)
    
    return files

# Utility functions for tests
def create_temp_file(temp_dir: str, filename: str, content: str) -> str:
    """Create a temporary file with content"""
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path

def create_jsonl_file(temp_dir: str, filename: str, records: list) -> str:
    """Create a JSONL file with records"""
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    return file_path

# Mock classes for testing
class MockSpacyDoc:
    """Mock spaCy document for testing"""
    def __init__(self, text: str):
        self.text = text
        # Simple sentence splitting for testing
        sentences = text.split('.')
        self.sents = [MockSpacySent(s.strip()) for s in sentences if s.strip()]

class MockSpacySent:
    """Mock spaCy sentence for testing"""
    def __init__(self, text: str):
        self.text = text

# Async test utilities
@pytest.fixture
async def async_mock():
    """Create async mock for testing"""
    mock = MagicMock()
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    return mock

# Database mocks
@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []
    return mock_conn