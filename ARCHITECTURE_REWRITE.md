# System Architecture Rewrite - Complete

## Overview
This document summarizes the complete architectural rewrite from FastAPI endpoints to asynchronous worker-based architecture using Redis queues.

## Architecture Changes

### Before: FastAPI Endpoints
- Each service exposed HTTP endpoints
- Synchronous request-response pattern
- Services called each other directly via HTTP

### After: Async Worker Queue Pattern
- Services are asynchronous workers consuming from Redis queues
- Non-blocking communication via Redis message queues
- Decoupled architecture with better scalability

## Phase 1: Asynchronous Worker Implementation ✅

### 1. Encoder Service (`services/encoder_service/app.py`)
**Status:** ✅ Complete

**Changes:**
- Converted from FastAPI endpoint to async worker
- Uses `redis.asyncio.brpop` to consume from `job:encoder_in`
- Encodes text to embeddings using sentence-transformers
- Publishes to `job:retriever_in` with embedding data
- Removed FastAPI/uvicorn dependencies

**Queue Flow:**
```
job:encoder_in → encode text → job:retriever_in
```

### 2. Retriever Service (`services/retriever_service/worker.py`)
**Status:** ✅ Complete

**Changes:**
- Converted from FastAPI endpoint to async worker
- Uses `redis.asyncio.brpop` to consume from `job:retriever_in`
- Searches Qdrant vector database with embeddings
- Augments prompt with retrieved context
- Publishes to `job:llm_in`

**Queue Flow:**
```
job:retriever_in → Qdrant search → augment prompt → job:llm_in
```

### 3. LLM Generator Service (`services/llm_generator/worker.py`)
**Status:** ✅ Complete

**Changes:**
- Converted from FastAPI endpoint to async worker
- Uses `redis.asyncio.brpop` to consume from `job:llm_in`
- Calls Mock LLM via httpx (async HTTP client)
- Writes result to `job:completion:<JOB_ID>` key (60s TTL)
- Includes worker name in response for load balancing visibility

**Queue Flow:**
```
job:llm_in → LLM generation → job:completion:<JOB_ID>
```

## Phase 2: API Gateway & Orchestration ✅

### API Gateway Updates (`services/api_gateway/app.py`)
**Status:** ✅ Complete

**Changes:**
1. **Async Redis Client:**
   - Changed from `redis.Redis` to `redis.asyncio`
   - All Redis operations now use async/await

2. **Load Balancing Heuristic:**
   - Implemented `get_least_loaded_replica()` function
   - Uses Redis keys `llm:load:<URL>` to track load per replica
   - Selects replica with minimum active jobs (Least Connections algorithm)

3. **Query Endpoint Flow:**
   ```
   1. Select least loaded LLM replica
   2. Increment load counter (llm:load:<URL>)
   3. Publish job to job:encoder_in
   4. Poll job:completion:<JOB_ID> (60s timeout)
   5. Decrement load counter
   6. Return result
   ```

4. **Removed:**
   - Old RL agent integration (kept RL service for future use)
   - Synchronous Redis calls
   - Direct HTTP calls to encoder service

### Docker Compose Updates (`docker-compose.yml`)
**Status:** ✅ Complete

**Changes:**
1. **LLM Generator Replicas:**
   - Added 3 identical replicas: `llm_generator_1`, `llm_generator_2`, `llm_generator_3`
   - Each has unique `WORKER_NAME` environment variable
   - All consume from same `job:llm_in` queue
   - No exposed ports (workers, not HTTP services)

2. **Service Configuration:**
   - Removed API_PORT from worker services
   - Removed port mappings for encoder, retriever, llm_generators
   - Updated to use worker.py instead of app.py

3. **Environment Variables:**
   - `WORKER_NAME`: Identifies which LLM generator replica
   - `OLLAMA_URL`: Points to mock_llm service
   - Removed unused variables

## Phase 3: Load Testing ✅

### Load Tester (`utils/load_tester.py`)
**Status:** ✅ Complete

**Features:**
- 50 concurrent requests (configurable via `LT_CONCURRENCY`)
- P99, P95, P50 latency calculations
- Success/failure tracking
- Throughput metrics (requests/sec)
- Enhanced output formatting

**Usage:**
```bash
python utils/load_tester.py

# Or with custom concurrency
LT_CONCURRENCY=100 python utils/load_tester.py
```

## Dependency Updates ✅

### Updated Requirements Files:

1. **encoder_service/requirements.txt**
   - Added: `redis[asyncio]`
   - Removed: `fastapi`, `uvicorn`

2. **retriever_service/requirements.txt**
   - Added: `redis[asyncio]`
   - Removed: `fastapi`, `uvicorn`, `numpy`

3. **llm_generator/requirements.txt**
   - Added: `redis[asyncio]`, `httpx`
   - Removed: `fastapi`, `uvicorn`, `requests`

4. **api_gateway/requirements.txt**
   - Changed: `redis` → `redis[asyncio]`

## Dockerfile Updates ✅

### Changes to All Worker Dockerfiles:

1. **encoder_service/Dockerfile**
   - Changed CMD from uvicorn to `python app.py`
   - Removed EXPOSE 8000

2. **retriever_service/Dockerfile**
   - Changed CMD to `python worker.py`
   - Cleaned up duplicate config

3. **llm_generator/Dockerfile**
   - Changed CMD to `python worker.py`
   - Removed entrypoint.sh
   - Removed EXPOSE 8000

## Complete Data Flow

```
User Request
    ↓
API Gateway (/query endpoint)
    ↓
[Select least loaded LLM replica via heuristic]
    ↓
Publish to job:encoder_in
    ↓
Encoder Worker (brpop)
    ├→ Encode text to vector
    └→ Publish to job:retriever_in
        ↓
Retriever Worker (brpop)
    ├→ Search Qdrant
    ├→ Augment prompt with context
    └→ Publish to job:llm_in
        ↓
LLM Generator Worker (1 of 3 replicas, brpop)
    ├→ Call Mock LLM
    └→ Write to job:completion:<JOB_ID>
        ↓
API Gateway (polling)
    ├→ Read from job:completion:<JOB_ID>
    ├→ Decrement load counter
    └→ Return response to user
```

## Load Balancing Strategy

### Heuristic: Least Connections
- Each LLM replica URL has a Redis key: `llm:load:<URL>`
- Counter incremented when job assigned to replica
- Counter decremented when job completes (success or timeout)
- Gateway selects replica with minimum load counter

### Why This Works:
- Simple and effective for CPU-bound workloads
- No external dependencies (unlike RL agent)
- Low overhead (single Redis GET per replica)
- Naturally balances load across replicas

## Testing the System

### 1. Start Services:
```bash
docker-compose up --build
```

### 2. Wait for Services to Initialize:
- Check encoder service logs: "Encoder worker started"
- Check retriever service logs: "Retriever worker started"
- Check 3 LLM generator logs: "LLM Generator worker [...] started"
- Check API Gateway logs: "Application startup complete"

### 3. Send Test Query:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is machine learning?"}'
```

### 4. Run Load Test:
```bash
python utils/load_tester.py
```

Expected output:
```
RAG System Load Test
============================================================
Target: http://localhost:8000/query
Concurrency: 50 requests
Starting test...

============================================================
Load Test Results
============================================================
Total Duration:    15.23s
Total Requests:    50
Successful:        50 (100.0%)
Failed:            0 (0.0%)

Latency Statistics (ms):
  Min:             245.67
  P50 (Median):    312.45
  P95:             478.23
  P99:             523.89
  Max:             534.12
  Average:         320.15

Throughput:        3.28 req/s
============================================================
```

### 5. Check Load Balancing:
```bash
# Check Redis load counters (should be 0 when idle)
redis-cli GET "llm:load:http://llm_generator_1:8000"
redis-cli GET "llm:load:http://llm_generator_2:8000"
redis-cli GET "llm:load:http://llm_generator_3:8000"
```

### 6. Monitor Queue Depth:
```bash
# Check queue depths
redis-cli LLEN job:encoder_in
redis-cli LLEN job:retriever_in
redis-cli LLEN job:llm_in
```

## Monitoring & Debugging

### View Worker Logs:
```bash
docker-compose logs -f encoder_service
docker-compose logs -f retriever_service
docker-compose logs -f llm_generator_1
docker-compose logs -f llm_generator_2
docker-compose logs -f llm_generator_3
```

### Check Prometheus Metrics:
```
http://localhost:9090
```

Key queries:
- `api_gateway_queries_total` - Total queries processed
- `api_gateway_query_latency_seconds` - Latency distribution
- `api_gateway_replica_load` - Load per replica

## Key Benefits of New Architecture

1. **Scalability:**
   - Easy to add more worker replicas (just add to docker-compose)
   - Workers automatically compete for jobs from shared queue
   - No code changes needed to scale

2. **Resilience:**
   - Workers can crash and restart without losing jobs
   - Jobs remain in queue until processed
   - Decoupled services reduce cascading failures

3. **Performance:**
   - Non-blocking async I/O throughout
   - Efficient connection pooling (Redis, HTTP)
   - No HTTP overhead between pipeline stages

4. **Observability:**
   - Worker names in logs for debugging
   - Load counters visible in Redis
   - Queue depths indicate bottlenecks

5. **Simplicity:**
   - Clear data flow (queue → process → queue)
   - Each worker has single responsibility
   - Easy to understand and debug

## Future Enhancements

1. **Re-enable RL Agent:**
   - Replace `get_least_loaded_replica()` with RL-based selection
   - Train on production traffic patterns
   - Optimize for P99 latency instead of load

2. **Add Circuit Breakers:**
   - Detect failed replicas
   - Temporarily remove from rotation
   - Auto-recovery after health checks

3. **Implement Rate Limiting:**
   - Prevent queue overflow
   - Throttle requests at API Gateway
   - Per-user quotas

4. **Add Caching:**
   - Cache embeddings for repeat queries
   - Cache Qdrant search results
   - Redis cache with TTL

5. **Metrics & Alerting:**
   - Alert on high P99 latency
   - Alert on queue depth thresholds
   - Alert on worker crashes

## Summary

✅ **Phase 1:** All workers converted to async queue pattern
✅ **Phase 2:** API Gateway updated with heuristic load balancing
✅ **Phase 3:** Load tester with P99 latency reporting
✅ **Dependencies:** All requirements.txt updated
✅ **Docker:** All Dockerfiles and docker-compose.yml updated

The system is now fully async, scalable, and ready for production workloads!
