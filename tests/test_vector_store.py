import pytest
import os
from unittest.mock import MagicMock, patch
from src.vector.store import VectorStore
from src.text.processor import TextChunk

@pytest.fixture
def mock_chroma_client():
    with patch('chromadb.PersistentClient') as mock_client:
        yield mock_client

@pytest.fixture
def vector_store(mock_chroma_client):
    # Mock settings.chroma_persist_directory
    with patch('src.config.settings.chroma_persist_directory', '/tmp/chroma_test'):
        with patch('src.config.settings.collection_name', 'test_collection'):
            store = VectorStore(collection_name="test_collection")
            return store

def test_get_content_no_collection(vector_store):
    # Ensure collection is None
    vector_store.collection = None
    content = vector_store.get_content()
    assert content == []

def test_get_content_with_results(vector_store):
    # Mock the collection object
    mock_collection = MagicMock()
    vector_store.collection = mock_collection
    
    # Mock the return value of collection.get()
    mock_collection.get.return_value = {
        'ids': ['id1', 'id2'],
        'documents': ['doc1', 'doc2'],
        'metadatas': [{'source': 'url1'}, {'source': 'url2'}]
    }
    
    content = vector_store.get_content(limit=10, offset=0)
    
    # Verify collection.get was called correctly
    mock_collection.get.assert_called_once_with(
        limit=10,
        offset=0,
        where=None,
        include=["documents", "metadatas"]
    )
    
    # Verify formatted results
    assert len(content) == 2
    assert content[0] == {'id': 'id1', 'document': 'doc1', 'metadata': {'source': 'url1'}}
    assert content[1] == {'id': 'id2', 'document': 'doc2', 'metadata': {'source': 'url2'}}

def test_get_content_with_where_filter(vector_store):
    mock_collection = MagicMock()
    vector_store.collection = mock_collection
    
    mock_collection.get.return_value = {
        'ids': ['id1'],
        'documents': ['doc1'],
        'metadatas': [{'source_url': 'http://example.com'}]
    }
    
    where = {"source_url": "http://example.com"}
    content = vector_store.get_content(where=where)
    
    mock_collection.get.assert_called_once_with(
        limit=None,
        offset=None,
        where=where,
        include=["documents", "metadatas"]
    )
    assert len(content) == 1

def test_get_content_error_handling(vector_store):
    mock_collection = MagicMock()
    vector_store.collection = mock_collection
    
    # Simulate an exception
    mock_collection.get.side_effect = Exception("ChromaDB error")
    
    content = vector_store.get_content()
    assert content == []
