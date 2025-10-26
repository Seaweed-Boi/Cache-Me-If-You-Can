# RAG App Migration Summary

## What Changed

### 1. **Removed OpenAI Dependency**
- **Before**: App required `OPENAI_API_KEY` and used `ChatOpenAI` for text generation
- **After**: App now uses local Hugging Face models via `transformers` pipeline
- **Config**: Set `LOCAL_MODEL_NAME` env variable to specify which HF model to use

### 2. **Replaced ChromaDB with Qdrant**
- **Before**: Used ChromaDB with local disk persistence (`./chroma_db`)
- **After**: Uses Qdrant vector database (separate container)
- **Benefits**: Better scalability, gRPC support, web dashboard at http://localhost:6333/dashboard

### 3. **Updated Dependencies**
Added to `requirements.txt`:
- `qdrant-client==1.7.1` - Qdrant Python client
- `transformers>=4.41.0` - Hugging Face transformers for local models
- `torch>=2.0.0` - PyTorch for model inference

Removed dependency on:
- `langchain-openai` (still installed but not used)

### 4. **Docker Compose Changes**
- Added `qdrant` service (port 6333)
- Updated `rag-app` environment variables:
  - Removed: `OPENAI_API_KEY`, `VECTOR_STORE_PATH`
  - Added: `LOCAL_MODEL_NAME`, `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`
- Removed Locust `--autostart` (UI now requires manual test start)

---

## Current Service Status

All services are **UP** and **HEALTHY**:

| Service | Status | Port | URL |
|---------|--------|------|-----|
| **rag-app** | ✅ Running | 8000 | http://localhost:8000 |
| **qdrant** | ✅ Running | 6333 | http://localhost:6333/dashboard |
| **prometheus** | ✅ Running | 9090 | http://localhost:9090 |
| **locust** | ✅ Running | 8089 | http://localhost:8089 |

### Prometheus Targets
- `prometheus`: **up** ✅
- `rag-api`: **up** ✅ (metrics at http://localhost:8000/metrics)

---

## How to Use

### 1. **Configure Local Model** (Required)

Before using the `/api/query` endpoint, set a local Hugging Face model:

```bash
# Edit .env file in project root
echo 'LOCAL_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0' >> .env

# Or use a larger model (requires more RAM/CPU):
# LOCAL_MODEL_NAME=meta-llama/Llama-2-7b-chat-hf
# LOCAL_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2
```

**Recommended starter model**: `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (small, fast, ~600MB download)

Then restart the app:
```bash
docker-compose up -d --no-deps --force-recreate rag-app
```

### 2. **Index Documents**

Add PDF files to `./data/` directory, then create the vector index:

```bash
# Add your PDFs
cp /path/to/your/*.pdf ./data/

# Index via API
curl -X POST http://localhost:8000/api/index
```

**Response example**:
```json
{
  "message": "Indexing complete. Vector store created successfully with 245 chunks indexed."
}
```

### 3. **Query the RAG System**

```bash
curl -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the main topic of the document?"}'
```

**Response example**:
```json
{
  "answer": "Based on the provided context, the document discusses..."
}
```

### 4. **Run Load Tests with Locust**

1. Open Locust UI: http://localhost:8089
2. Configure:
   - **Number of users**: 10
   - **Spawn rate**: 2
   - **Host**: http://rag-app:8000 (pre-configured)
3. Click **Start swarming**
4. View real-time stats and charts

### 5. **Monitor with Prometheus**

- **Prometheus UI**: http://localhost:9090
- **Metrics endpoint**: http://localhost:8000/metrics
- **Sample query**: `http_requests_total{job="rag-api"}`

---

## Quick Commands

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f rag-app
docker-compose logs -f qdrant
```

### Rebuild after code changes
```bash
docker-compose up -d --build rag-app
```

### Check service status
```bash
docker-compose ps
```

### Check Qdrant collections
```bash
curl http://localhost:6333/collections
```

---

## Known Issues & Notes

### 1. **Local Model Required**
- If `LOCAL_MODEL_NAME` is not set, `/api/query` will return an error:
  ```
  "No local model configured. Set LOCAL_MODEL_NAME in your .env or settings..."
  ```
- **Fix**: Set the env var and restart the container

### 2. **First Query is Slow**
- The first query downloads and loads the HF model (~600MB for TinyLlama)
- Subsequent queries are faster (model stays loaded in memory)

### 3. **Deprecation Warnings** (Harmless)
- LangChain import warnings appear in logs but don't affect functionality
- Will be cleaned up in future updates

### 4. **Memory Usage**
- TinyLlama: ~1-2GB RAM
- Larger models (7B+): 8-16GB+ RAM
- Adjust Docker Desktop memory limits if needed

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Locust    │────▶│   rag-app    │────▶│   Qdrant     │
│  (Port 8089)│     │  (Port 8000) │     │  (Port 6333) │
└─────────────┘     └──────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Prometheus  │
                    │  (Port 9090) │
                    └──────────────┘
```

- **rag-app**: FastAPI application with RAG pipeline
- **qdrant**: Vector database for document embeddings
- **prometheus**: Metrics collection and monitoring
- **locust**: Load testing and performance analysis

---

## Next Steps

1. ✅ Set `LOCAL_MODEL_NAME` in `.env`
2. ✅ Add PDF files to `./data/`
3. ✅ Run `/api/index` to create vector store
4. ✅ Test with `/api/query`
5. ✅ Run load tests via Locust UI
6. ✅ Monitor metrics in Prometheus

---

## Troubleshooting

### rag-app returns 500 errors
```bash
# Check logs
docker-compose logs rag-app --tail=50

# Common causes:
# - LOCAL_MODEL_NAME not set
# - Qdrant not running
# - Model download failed (check network)
```

### Qdrant connection errors
```bash
# Verify Qdrant is running
docker-compose ps qdrant

# Check Qdrant health
curl http://localhost:6333/health
```

### Out of memory
```bash
# Use a smaller model
LOCAL_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Or increase Docker memory in Docker Desktop settings
```

---

**Migration completed**: `2025-10-26`
