"""
Retriever Service Worker - Continuous job processor
Pops jobs from job:retriever_in, searches Qdrant, augments prompt, pushes to job:llm_in
"""
import os
import time
import json
import asyncio
from dotenv import load_dotenv
from redis import asyncio as aioredis
from qdrant_client import QdrantClient

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")
TOP_K = int(os.getenv("TOP_K", 5))

QUEUE_IN = "job:retriever_in"
QUEUE_OUT = "job:llm_in"

# Global Qdrant client
_qdrant = None


def get_qdrant_client():
    """Get or create Qdrant client"""
    global _qdrant
    if _qdrant is None:
        print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        _qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print("✓ Connected to Qdrant")
    return _qdrant


def search_qdrant(embedding: list, top_k: int = TOP_K) -> list:
    """Search Qdrant for similar documents"""
    client = get_qdrant_client()
    
    try:
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=top_k
        )
        
        # Extract text from results
        contexts = []
        for hit in results:
            if hasattr(hit, 'payload') and 'text' in hit.payload:
                contexts.append(hit.payload['text'])
        
        return contexts
    except Exception as e:
        print(f"Qdrant search error: {e}")
        return []


def build_augmented_prompt(query: str, contexts: list) -> str:
    """Build RAG prompt with retrieved context"""
    if not contexts:
        return query
    
    context_str = "\n\n".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)])
    
    prompt = f"""You are a helpful assistant. Use the following context to answer the question.

Context:
{context_str}

Question: {query}

Answer:"""
    
    return prompt


async def worker_loop():
    """
    Main worker loop - continuously process retrieval jobs
    
    Flow:
    1. Pop job from job:retriever_in (blocking)
    2. Search Qdrant with embedding
    3. Augment prompt with retrieved context
    4. Push enhanced job to job:llm_in
    """
    # Connect to Redis
    redis = await aioredis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}",
        decode_responses=True
    )
    
    print(f"Retriever worker started, listening on {QUEUE_IN}")
    
    # Initialize Qdrant client at startup
    get_qdrant_client()
    
    while True:
        try:
            # Blocking pop from input queue (timeout 5 seconds)
            result = await redis.brpop(QUEUE_IN, timeout=5)
            
            if not result:
                # Timeout, no job available
                await asyncio.sleep(0.1)
                continue
            
            _, job_data = result
            job = json.loads(job_data)
            
            job_id = job.get("job_id")
            query = job.get("text") or job.get("query")
            embedding = job.get("embedding")
            
            if not job_id or not query or not embedding:
                print(f"Invalid job, missing required fields: {job}")
                continue
            
            print(f"[{job_id}] Retrieving context for: {query[:50]}...")
            
            # Search Qdrant
            start_time = time.time()
            contexts = search_qdrant(embedding, top_k=TOP_K)
            retrieve_time = (time.time() - start_time) * 1000
            
            print(f"[{job_id}] Retrieved {len(contexts)} contexts in {retrieve_time:.1f}ms")
            
            # Build augmented prompt
            augmented_prompt = build_augmented_prompt(query, contexts)
            
            # Update job payload
            job["contexts"] = contexts
            job["augmented_prompt"] = augmented_prompt
            job["retrieve_time_ms"] = retrieve_time
            job["num_contexts"] = len(contexts)
            
            # Push to LLM queue
            await redis.lpush(QUEUE_OUT, json.dumps(job))
            print(f"[{job_id}] Pushed to {QUEUE_OUT}")
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(1)


async def main():
    """Entry point"""
    try:
        await worker_loop()
    except KeyboardInterrupt:
        print("\nShutting down retriever worker")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
