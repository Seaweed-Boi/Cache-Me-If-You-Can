import os
import time
import json
import asyncio
import uuid
import requests
from typing import List, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import asyncio as aioredis
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# --- Configuration & Initialization ---
load_dotenv()

# Service URLs (Uses Docker service names from .env)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
RL_AGENT_URL = os.getenv("RL_AGENT_URL", "http://rl_agent:5000")
USE_RL_AGENT = os.getenv("USE_RL_AGENT", "true").lower() == "true"

# List of LLM Generator Replicas (3 identical workers)
LLM_REPLICAS = [
    "http://llm_generator_1:8000",
    "http://llm_generator_2:8000",
    "http://llm_generator_3:8000",
]

# --- Redis Connection ---
redis_client = None

async def get_redis():
    """Get or create async Redis connection"""
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}",
            decode_responses=True
        )
    return redis_client

# --- FastAPI Setup & Models ---
app = FastAPI(title="API Gateway (RL Heuristic)", version="1.0")

# --- Prometheus Metrics ---
query_counter = Counter('api_gateway_queries_total', 'Total queries processed', ['status'])
query_latency = Histogram('api_gateway_query_latency_seconds', 'Query latency in seconds', buckets=[0.1, 0.5, 1, 5, 10, 30, 60])
active_jobs = Gauge('api_gateway_active_jobs', 'Number of active jobs')
replica_load = Gauge('api_gateway_replica_load', 'Load on each replica', ['replica_index'])

class QueryInput(BaseModel):
    """External user query input."""
    query: str

class FinalResponse(BaseModel):
    """Final, aggregated response to the user."""
    job_id: str
    answer: str
    latency_ms: float
    selected_replica: str

# --- Load Balancing Heuristic (CRITICAL LOGIC) ---
async def get_least_loaded_replica() -> Tuple[str, int]:
    """
    Heuristic load balancing: finds the replica with the fewest active jobs (Least Connections).
    Uses Redis keys llm:load:<URL> to track load per replica.
    """
    redis = await get_redis()
    
    min_load = float('inf')
    best_replica_url = LLM_REPLICAS[0]
    best_index = 0

    for idx, replica_url in enumerate(LLM_REPLICAS):
        load_key = f"llm:load:{replica_url}"
        try:
            current_load_str = await redis.get(load_key)
            current_load = int(current_load_str) if current_load_str else 0
        except Exception:
            current_load = 0

        # Choose the replica with the minimum load
        if current_load < min_load:
            min_load = current_load
            best_replica_url = replica_url
            best_index = idx

    return best_replica_url, best_index


# --- Prometheus Metrics Endpoint ---
@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- Main Orchestration Endpoint ---
@app.post("/query", response_model=FinalResponse)
async def process_rag_query(input: QueryInput):
    """
    Orchestrates the full RAG pipeline with async workers:
    1. Select least loaded LLM replica
    2. Publish job to encoder queue
    3. Poll for completion key
    4. Return result
    """
    start_time = time.time()
    active_jobs.inc()
    
    try:
        # Get Redis connection
        redis = await get_redis()
        
        # Generate a unique job id
        job_id = str(uuid.uuid4())

        # Select least loaded replica
        replica_url, replica_idx = await get_least_loaded_replica()
        load_key = f"llm:load:{replica_url}"
        
        # Increment load counter for selected replica
        try:
            await redis.incr(load_key)
            current_load_str = await redis.get(load_key)
            current_load = int(current_load_str) if current_load_str else 0
            replica_load.labels(replica_index=str(replica_idx)).set(current_load)
        except Exception as e:
            print(f"Failed to increment load: {e}")

        # Publish job to encoder queue
        job_payload = {
            "job_id": job_id,
            "text": input.query,
            "selected_replica": replica_url,
            "timestamp": time.time()
        }
        
        try:
            await redis.lpush("job:encoder_in", json.dumps(job_payload))
            print(f"[{job_id}] Published to encoder queue, replica: {replica_url}")
        except Exception as e:
            # If publish failed, decrement load
            try:
                await redis.decr(load_key)
            except Exception:
                pass
            query_counter.labels(status='error').inc()
            raise HTTPException(status_code=503, detail=f"Failed to publish job: {e}")

        # Poll for completion key (60 second timeout)
        completion_key = f"job:completion:{job_id}"
        result = None
        timeout = 60.0
        poll_interval = 0.25
        elapsed = 0.0
        
        try:
            while elapsed < timeout:
                raw = await redis.get(completion_key)
                if raw:
                    try:
                        result = json.loads(raw)
                        break
                    except Exception:
                        result = {"response": str(raw)}
                        break
                await asyncio.sleep(poll_interval)
                elapsed = time.time() - start_time
        finally:
            # Decrement load counter regardless of success/timeout
            try:
                new_val = await redis.decr(load_key)
                if new_val is not None and int(new_val) < 0:
                    await redis.set(load_key, 0)
                    new_val = 0
                replica_load.labels(replica_index=str(replica_idx)).set(max(0, int(new_val or 0)))
            except Exception as e:
                print(f"Failed to decrement load: {e}")

        end_time = time.time()
        e2e_latency = (end_time - start_time) * 1000
        latency_seconds = (end_time - start_time)

        if not result:
            query_counter.labels(status='timeout').inc()
            raise HTTPException(status_code=504, detail="Job timed out before completion")

        if not result.get("success", True):
            query_counter.labels(status='error').inc()
            raise HTTPException(status_code=500, detail=result.get("error", "LLM generation failed"))

        query_counter.labels(status='success').inc()
        query_latency.observe(latency_seconds)

        return FinalResponse(
            job_id=job_id,
            answer=result.get("response", ""),
            latency_ms=e2e_latency,
            selected_replica=replica_url
        )
    
    finally:
        active_jobs.dec()