from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.config.settings import settings
from src.utils.loader import load_documents

# Qdrant and LangChain Qdrant wrapper
from qdrant_client import QdrantClient
from langchain_community.vectorstores import Qdrant


def create_vector_store():
    """
    Build and persist a vector store from PDF documents.
    
    This function:
    1. Loads PDF documents from the configured data path
    2. Splits documents into chunks
    3. Creates embeddings using HuggingFace models
    4. Stores embeddings in a Qdrant vector database
    5. Persists the vector store to Qdrant
    
    Returns:
        Qdrant: The created and persisted vector store
    """
    print("=" * 50)
    print("Starting Vector Store Creation")
    print("=" * 50)
    
    # Step 1: Load documents from the data path
    print(f"\n1. Loading documents from: {settings.data_path}")
    documents = load_documents(settings.data_path)
    
    if not documents:
        raise ValueError("No documents loaded. Please add PDF files to the data directory.")
    
    # Step 2: Split documents into chunks
    print(f"\n2. Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"  Created {len(chunks)} chunks from {len(documents)} documents")
    
    # Step 3: Initialize embedding model
    print(f"\n3. Initializing embedding model: {settings.embedding_model_name}")
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    print("  Embedding model initialized successfully")
    
    # Step 4: Create and persist Qdrant vector store
    print(f"\n4. Creating Qdrant vector store collection: {settings.qdrant_collection} @ {settings.qdrant_host}:{settings.qdrant_port}")
    qdrant_client = QdrantClient(url=f"http://{settings.qdrant_host}:{settings.qdrant_port}")

    vector_store = Qdrant.from_documents(
        documents=chunks,
        embedding=embeddings,
        client=qdrant_client,
        collection_name=settings.qdrant_collection
    )
    print("  Vector store (Qdrant) created and persisted successfully")
    
    print("\n" + "=" * 50)
    print("Vector Store Creation Complete!")
    print("=" * 50)
    print(f"Total chunks indexed: {len(chunks)}")
    print(f"Vector store collection: {settings.qdrant_collection} on {settings.qdrant_host}:{settings.qdrant_port}")
    
    return vector_store


if __name__ == "__main__":
    # Allow running this script directly to create the vector store
    try:
        create_vector_store()
        print("\n✓ Vector store built successfully!")
    except Exception as e:
        print(f"\n✗ Error creating vector store: {str(e)}")
        raise
