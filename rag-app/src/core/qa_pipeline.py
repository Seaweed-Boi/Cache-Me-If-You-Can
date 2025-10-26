from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from src.config.settings import settings

# Qdrant and local generation
from qdrant_client import QdrantClient
from langchain_community.vectorstores import Qdrant
from transformers import pipeline


# Define the RAG prompt template
RAG_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based on the provided context.

Use the following pieces of context to answer the question at the end. 
If you don't know the answer based on the context, just say that you don't know, don't try to make up an answer.
Keep your answer concise and relevant to the question.

Context:
{context}

Question: {question}

Answer:"""


def format_docs(docs):
    """
    Format retrieved documents into a single string for the prompt.
    
    Args:
        docs: List of Document objects retrieved from the vector store
        
    Returns:
        Formatted string containing all document contents
    """
    return "\n\n".join(doc.page_content for doc in docs)


def get_rag_answer(query: str) -> str:
    """
    Get an answer to a query using Retrieval-Augmented Generation (RAG).
    
    This function:
    1. Initializes the LLM (ChatOpenAI)
    2. Loads the persisted vector store
    3. Retrieves relevant documents for the query
    4. Formats a prompt with context and query
    5. Generates an answer using the LLM
    
    Args:
        query: The user's question
        
    Returns:
        The generated answer as a string
        
    Raises:
        ValueError: If the vector store doesn't exist or is empty
        Exception: If there's an error with the OpenAI API
    """
    print(f"\nProcessing query: {query}")
    
    # Step 1: Initialize the embedding model (same as used during indexing)
    print(f"2. Initializing embedding model: {settings.embedding_model_name}")
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Step 3: Load the existing persisted Qdrant vector store
    print(f"3. Loading vector store from Qdrant collection: {settings.qdrant_collection}")
    qdrant_client = QdrantClient(url=f"http://{settings.qdrant_host}:{settings.qdrant_port}")
    vector_store = Qdrant(
        client=qdrant_client,
        collection_name=settings.qdrant_collection,
        embeddings=embeddings
    )
    
    # Step 4: Create a retriever from the vector store
    print("4. Creating retriever...")
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}  # Retrieve top 4 most relevant chunks
    )
    
    # Step 5: Define the prompt template
    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    
    # Step 6: Build prompt with retrieved context and generate answer.
    print("5. Building prompt and generating answer with local model...")
    full_prompt = prompt.format(context=format_docs(retriever.get_relevant_documents(query)), question=query)

    # Use local HF model if provided
    if settings.local_model_name:
        gen = pipeline(
            "text-generation",
            model=settings.local_model_name,
            device=-1,
            trust_remote_code=True
        )
        outputs = gen(full_prompt, max_new_tokens=256, do_sample=False)
        answer = outputs[0]["generated_text"]
    else:
        raise RuntimeError("No local model configured. Set LOCAL_MODEL_NAME in your .env or settings to use a local model.")
    
    print("✓ Answer generated successfully\n")
    return answer


if __name__ == "__main__":
    # Example usage when running this script directly
    import sys
    
    if len(sys.argv) > 1:
        # Use command-line argument as query
        user_query = " ".join(sys.argv[1:])
    else:
        # Default test query
        user_query = "What is this document about?"
    
    try:
        answer = get_rag_answer(user_query)
        print("=" * 50)
        print("ANSWER:")
        print("=" * 50)
        print(answer)
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        raise
