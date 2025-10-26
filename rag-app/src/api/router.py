from fastapi import APIRouter, HTTPException, status
from src.api.schemas import QueryRequest, QueryResponse, IndexResponse
from src.core.indexing import create_vector_store
from src.core.qa_pipeline import get_rag_answer


# Create the API router
router = APIRouter(
    prefix="/api",
    tags=["RAG Pipeline"]
)


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question using RAG",
    description="Submit a question to get an answer based on the indexed documents using Retrieval-Augmented Generation."
)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """
    Query the RAG system with a question.
    
    Args:
        request: QueryRequest containing the user's question
        
    Returns:
        QueryResponse with the generated answer
        
    Raises:
        HTTPException: If there's an error processing the query
    """
    try:
        # Get the answer using the RAG pipeline
        answer = get_rag_answer(request.query)
        
        return QueryResponse(answer=answer)
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vector store not found. Please run the /index endpoint first. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.post(
    "/index",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create vector store index",
    description="Load PDF documents from the data directory, create embeddings, and build the vector store index."
)
async def index_documents() -> IndexResponse:
    """
    Create or rebuild the vector store index.
    
    This endpoint:
    1. Loads all PDF documents from the configured data directory
    2. Splits them into chunks
    3. Creates embeddings
    4. Stores them in the Qdrant vector database
    
    Returns:
        IndexResponse with a success message
        
    Raises:
        HTTPException: If there's an error during indexing
    """
    try:
        # Create the vector store
        vector_store = create_vector_store()

        # Query Qdrant to count indexed chunks
        from qdrant_client import QdrantClient
        from src.config.settings import settings as _settings

        q_client = QdrantClient(url=f"http://{_settings.qdrant_host}:{_settings.qdrant_port}")
        info = q_client.collection_info(collection_name=_settings.qdrant_collection)
        chunk_count = info.points_count if info is not None else 0

        return IndexResponse(
            message=f"Indexing complete. Vector store created successfully with {chunk_count} chunks indexed."
        )
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data directory or files not found: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during indexing: {str(e)}"
        )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is running"
)
async def health_check():
    """
    Simple health check endpoint.
    
    Returns:
        Status message indicating the API is healthy
    """
    return {"status": "healthy", "message": "RAG API is running"}
