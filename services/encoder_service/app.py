"""
Encoder Service Worker - Continuous job processor
Pops jobs from job:encoder_in, encodes text to vectors, pushes to job:retriever_in
"""
import os
import time
import json
import asyncio
import numpy as np
from dotenv import load_dotenv
from redis import asyncio as aioredis

load_dotenv()

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 384))
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_IN = "job:encoder_in"
QUEUE_OUT = "job:retriever_in"

# Global model instance
_model = None


def load_model():
    """Load the sentence transformer model"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading model: {MODEL_NAME}")
            _model = SentenceTransformer(MODEL_NAME, device=EMBEDDING_DEVICE)
            print(f"✓ Model loaded successfully")
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise
    return _model


def encode_text(text: str) -> np.ndarray:
    """Encode text to vector embedding"""
    model = load_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


async def worker_loop():
    """
    Main worker loop - continuously process encoding jobs
    
    Flow:
    1. Pop job from job:encoder_in (blocking)
    2. Encode the text to vector
    3. Push enhanced job to job:retriever_in
    """
    # Connect to Redis
    redis = await aioredis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}",
        decode_responses=True
    )
    
    print(f"Encoder worker started, listening on {QUEUE_IN}")
    
    # Load model once at startup
    load_model()
    
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
            text = job.get("text") or job.get("query")
            
            if not job_id or not text:
                print(f"Invalid job, missing job_id or text: {job}")
                continue
            
            print(f"[{job_id}] Encoding text: {text[:50]}...")
            
            # Encode the text
            start_time = time.time()
            embedding = encode_text(text)
            encode_time = (time.time() - start_time) * 1000
            
            print(f"[{job_id}] Encoded in {encode_time:.1f}ms, vector dim: {len(embedding)}")
            
            # Add embedding to job payload
            job["embedding"] = embedding.tolist()
            job["encode_time_ms"] = encode_time
            
            # Push to retriever queue
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
        print("\nShutting down encoder worker")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
