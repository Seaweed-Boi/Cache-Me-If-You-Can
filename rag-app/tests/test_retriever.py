from src.core.retriever import Retriever
import pytest

@pytest.fixture
def retriever():
    return Retriever()

def test_retrieve_documents(retriever):
    query = "example query"
    expected_documents = ["doc1", "doc2"]  # Replace with expected output
    retrieved_documents = retriever.retrieve(query)
    assert retrieved_documents == expected_documents

def test_empty_query(retriever):
    query = ""
    retrieved_documents = retriever.retrieve(query)
    assert retrieved_documents == []  # Expecting no documents for empty query

def test_invalid_query(retriever):
    query = "invalid query"
    retrieved_documents = retriever.retrieve(query)
    assert retrieved_documents == []  # Expecting no documents for invalid query