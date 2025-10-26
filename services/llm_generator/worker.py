"""
LLM Generator Worker - Continuous job processor
Pops jobs from job:llm_in, generates LLM response, writes to job:completion:<JOB_ID>
"""
import os
import time
import json
import asyncio
import httpx
from dotenv import load_dotenv
from redis import asyncio as aioredis

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://mock_llm:5000/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
GENERATION_TIMEOUT = int(os.getenv("GENERATION_TIMEOUT", 30))
WORKER_NAME = os.getenv("WORKER_NAME", "llm_generator_1")

QUEUE_IN = "job:llm_in"

# Global HTTP client for efficient connection pooling
_http_client = None


def get_http_client():
    """Get or create HTTP client"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=GENERATION_TIMEOUT)
    return _http_client


async def generate_response(prompt: str) -> dict:
    """Call LLM to generate response"""
    client = get_http_client()
    
    try:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            "success": True,
            "response": data.get("response", ""),
            "model": data.get("model", OLLAMA_MODEL)
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "LLM request timed out"
        }
    except httpx.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Generation error: {str(e)}"
        }


async def worker_loop():
    """
    Main worker loop - continuously process LLM generation jobs
    
    Flow:
    1. Pop job from job:llm_in (blocking)
    2. Call LLM to generate response
    3. Write result to job:completion:<JOB_ID>
    """
    # Connect to Redis
    redis = await aioredis.from_url(
        f"redis://{REDIS_HOST}:{REDIS_PORT}",
        decode_responses=True
    )
    
    print(f"LLM Generator worker [{WORKER_NAME}] started, listening on {QUEUE_IN}")
    
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
            prompt = job.get("augmented_prompt") or job.get("prompt") or job.get("text")
            
            if not job_id or not prompt:
                print(f"Invalid job, missing job_id or prompt: {job}")
                continue
            
            print(f"[{job_id}] Generating response with {WORKER_NAME}...")
            
            # Generate LLM response
            start_time = time.time()
            result = await generate_response(prompt)
            generation_time = (time.time() - start_time) * 1000
            
            # Build completion payload
            completion = {
                "job_id": job_id,
                "success": result["success"],
                "worker": WORKER_NAME,
                "generation_time_ms": generation_time,
                "timestamp": time.time()
            }
            
            if result["success"]:
                completion["response"] = result["response"]
                completion["model"] = result["model"]
                print(f"[{job_id}] Generated in {generation_time:.1f}ms by {WORKER_NAME}")
            else:
                completion["error"] = result["error"]
                print(f"[{job_id}] Generation failed: {result['error']}")
            
            # Write to completion key
            completion_key = f"job:completion:{job_id}"
            await redis.setex(
                completion_key,
                60,  # 60 second TTL
                json.dumps(completion)
            )
            print(f"[{job_id}] Result written to {completion_key}")
            
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
        print(f"\nShutting down LLM generator worker [{WORKER_NAME}]")
    except Exception as e:
        print(f"Fatal error: {e}")
        raise
    finally:
        # Cleanup HTTP client
        if _http_client:
            await _http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
