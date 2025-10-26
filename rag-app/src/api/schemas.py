from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Request model for question-answering queries.
    """
    query: str = Field(
        ...,
        description="The user's question to be answered using RAG",
        min_length=1,
        example="What is the main topic discussed in the documents?"
    )


class QueryResponse(BaseModel):
    """
    Response model for question-answering queries.
    """
    answer: str = Field(
        ...,
        description="The generated answer based on the retrieved context",
        example="The main topic discussed in the documents is artificial intelligence and machine learning."
    )


class IndexResponse(BaseModel):
    """
    Response model for indexing operations.
    """
    message: str = Field(
        ...,
        description="Status message about the indexing operation",
        example="Vector store created successfully with 150 chunks indexed."
    )
