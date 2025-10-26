# RAG Application Architecture

## System Overview

This document describes the architecture of the observable RAG (Retrieval-Augmented Generation) application with integrated monitoring and load testing.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                        │
│                          (rag-network)                               │
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────┐                    │
│  │   Locust         │      │   Prometheus     │                    │
│  │   Load Tester    │─────▶│   Monitoring     │                    │
│  │   :8089          │      │   :9090          │                    │
│  └────────┬─────────┘      └─────────▲────────┘                    │
│           │                          │                              │
│           │ HTTP                     │ Scrapes /metrics             │
│           │ Requests                 │ every 10s                    │
│           │                          │                              │
│           ▼                          │                              │
│  ┌───────────────────────────────────┴──────────────────────────┐  │
│  │              RAG Application (FastAPI)                        │  │
│  │                     :8000                                     │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐    │  │
│  │  │  Prometheus Instrumentator                          │    │  │
│  │  │  - Tracks HTTP requests                             │    │  │
│  │  │  - Response times                                   │    │  │
│  │  │  - Status codes                                     │    │  │
│  │  │  - In-progress requests                             │    │  │
│  │  └─────────────────────────────────────────────────────┘    │  │
│  │                                                               │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │  │
│  │  │ API Router   │  │ Core Logic   │  │ Data Layer   │      │  │
│  │  │              │  │              │  │              │      │  │
│  │  │ /api/query   │─▶│ RAG Pipeline │─▶│ ChromaDB     │      │  │
│  │  │ /api/index   │  │ Indexing     │  │ Vector Store │      │  │
│  │  │ /api/health  │  │ Q&A System   │  │              │      │  │
│  │  │ /metrics     │  │              │  │              │      │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   OpenAI API     │
                    │   (GPT-3.5)      │
                    └──────────────────┘
```

## Component Details

### 1. RAG Application (FastAPI)

**Ports**: 8000  
**Base Image**: python:3.10-slim  
**Purpose**: Main application serving API endpoints

#### Key Modules:

- **main.py**: FastAPI app initialization with Prometheus instrumentation
- **api/router.py**: API endpoints definition
- **api/schemas.py**: Pydantic models for validation
- **core/indexing.py**: Document loading and vector store creation
- **core/qa_pipeline.py**: RAG question-answering logic
- **config/settings.py**: Configuration management
- **utils/loader.py**: PDF document loading utilities

#### Endpoints:

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|--------------|
| `/` | GET | Health check | < 10ms |
| `/api/query` | POST | Answer questions | 1-3s |
| `/api/index` | POST | Build vector store | 30-120s |
| `/api/health` | GET | API health check | < 10ms |
| `/metrics` | GET | Prometheus metrics | < 50ms |
| `/docs` | GET | OpenAPI docs | < 20ms |

### 2. Prometheus

**Ports**: 9090  
**Image**: prom/prometheus:latest  
**Purpose**: Metrics collection and time-series database

#### Configuration:

- **Scrape interval**: 10 seconds
- **Retention**: 7 days
- **Target**: `rag-app:8000/metrics`

#### Key Metrics Collected:

```promql
# Request metrics
http_requests_total{method, handler, status}
http_request_duration_seconds_bucket{method, handler}
http_requests_inprogress{method, handler}

# Process metrics
process_cpu_seconds_total
process_resident_memory_bytes
process_open_fds

# Python metrics
python_gc_collections_total
python_info
```

### 3. Locust

**Ports**: 8089  
**Image**: locustio/locust:latest  
**Purpose**: Load testing and performance validation

#### Configuration:

- **Users**: 10 (configurable)
- **Spawn rate**: 2 users/second
- **Target**: `http://rag-app:8000`
- **Mode**: Standalone with autostart

#### Test Scenarios:

```python
Task Weights:
- query_endpoint:  10x (most frequent)
- health_check:     5x (regular monitoring)
- index_endpoint:   1x (occasional heavy operation)
```

## Data Flow

### Query Request Flow

```
1. User/Locust → POST /api/query
                  {"query": "What is AI?"}
   
2. FastAPI Router → Validate with QueryRequest schema
   
3. RAG Pipeline → Load vector store from disk
                → Initialize embeddings model
                → Embed user query
   
4. ChromaDB → Similarity search
            → Return top 4 relevant chunks
   
5. RAG Pipeline → Format chunks as context
                → Create prompt template
                → Call OpenAI API
   
6. OpenAI API → Generate answer
              → Return completion
   
7. Response → {"answer": "AI is..."}
   
8. Instrumentator → Record metrics:
                   - Request count
                   - Duration
                   - Status code
```

### Indexing Flow

```
1. User → POST /api/index

2. Indexing Module → Load PDFs from /app/data
                   → Parse PDFs with PyPDF
   
3. Text Splitter → Split into chunks (1000 chars, 200 overlap)
   
4. Embeddings → Load HuggingFace model (all-MiniLM-L6-v2)
              → Generate embeddings for each chunk
   
5. ChromaDB → Create/update vector store
            → Persist to /app/chroma_db
   
6. Response → {"message": "Indexing complete. 150 chunks indexed."}
```

### Metrics Collection Flow

```
1. Prometheus → Every 10s, scrape /metrics
   
2. RAG App → Instrumentator aggregates:
           - Request counts by endpoint
           - Duration histograms
           - In-progress requests
           - System metrics
   
3. Prometheus → Store time-series data
              → Retain for 7 days
   
4. User → Query Prometheus UI
        → View graphs and alerts
```

## Technology Stack

### Application Layer

- **FastAPI**: Web framework (async, high-performance)
- **Pydantic**: Data validation and settings
- **Uvicorn**: ASGI server

### RAG Components

- **LangChain**: Orchestration framework
  - `langchain-core`: Base functionality
  - `langchain-openai`: OpenAI integration
  - `langchain-community`: Community tools
- **ChromaDB**: Vector database
- **Sentence-Transformers**: Embedding generation
- **PyPDF**: PDF document parsing

### LLM & Embeddings

- **OpenAI GPT-3.5-turbo**: Language model
- **all-MiniLM-L6-v2**: Embedding model (HuggingFace)

### Monitoring

- **prometheus-fastapi-instrumentator**: Metrics collection
- **Prometheus**: Time-series database
- **Locust**: Load testing framework

### Infrastructure

- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## Storage & Persistence

### Volumes

```yaml
volumes:
  - ./data:/app/data                    # PDF documents (read-only)
  - ./chroma_db:/app/chroma_db          # Vector store (read-write)
  - prometheus-data:/prometheus         # Metrics data (managed)
```

### Directory Structure

```
/app/
├── data/                # PDF documents
│   ├── doc1.pdf
│   └── doc2.pdf
├── chroma_db/           # ChromaDB storage
│   ├── chroma.sqlite3
│   └── index/
├── src/                 # Application code
└── .env                 # Environment variables
```

## Network Architecture

### Docker Network: `rag-network`

All services communicate via a bridge network:

```
rag-app:8000       → Exposed to host as localhost:8000
prometheus:9090    → Exposed to host as localhost:9090
locust:8089        → Exposed to host as localhost:8089

Internal DNS:
- rag-app      → 172.18.0.2:8000
- prometheus   → 172.18.0.3:9090
- locust       → 172.18.0.4:8089
```

### Security Considerations

1. **Network Isolation**: Services isolated in Docker network
2. **No External Database**: Embedded ChromaDB
3. **API Key Security**: Loaded from environment variables
4. **CORS**: Configured for allowed origins
5. **Health Checks**: Docker health checks for reliability

## Scalability Considerations

### Current Limitations

- Single instance (monolithic)
- In-memory vector store loading
- Synchronous indexing
- No caching layer

### Future Improvements

1. **Horizontal Scaling**:
   ```yaml
   deploy:
     replicas: 3
     mode: replicated
   ```

2. **Caching**:
   - Redis for query results
   - Cached embeddings

3. **Async Processing**:
   - Background indexing with Celery
   - Async vector store operations

4. **Database**:
   - Persistent vector store (Pinecone, Weaviate)
   - Separate metadata database

## Monitoring & Observability

### Metrics Dashboard (Prometheus)

Key queries for monitoring:

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time (95th percentile)
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
process_resident_memory_bytes / 1024 / 1024

# Active requests
http_requests_inprogress
```

### Load Testing (Locust)

Continuous testing provides:
- Real-time performance metrics
- Breaking point identification
- Regression detection
- Capacity planning data

## Configuration Management

### Environment Variables

```bash
OPENAI_API_KEY          # Required: OpenAI API key
EMBEDDING_MODEL_NAME    # Optional: HuggingFace model name
VECTOR_STORE_PATH       # Optional: ChromaDB path
DATA_PATH               # Optional: PDF directory path
ENABLE_METRICS          # Optional: Enable Prometheus metrics
```

### Service Configuration

- **prometheus.yml**: Prometheus scrape config
- **locustfile.py**: Load test scenarios
- **docker-compose.yml**: Service orchestration
- **Dockerfile**: Container build instructions

## Deployment Models

### Development (Current)

```bash
docker-compose up -d
```

- Source code mounted as volume
- Live reload enabled
- Debug logging
- Local network only

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Recommended changes:
- Remove source code volume mount
- Use production ASGI server config
- Enable HTTPS
- Configure resource limits
- Set up log aggregation
- Add Grafana for visualization
- Configure Alertmanager

## Performance Benchmarks

### Expected Metrics (Standard Hardware)

| Metric | Value |
|--------|-------|
| Health check latency | < 10ms |
| Query latency (p50) | 1-2s |
| Query latency (p95) | 2-3s |
| Indexing time (100 pages) | 60-90s |
| Max concurrent users | 50-100 |
| Max requests/sec | 10-20 (queries) |

### Bottlenecks

1. **OpenAI API**: Rate limits and latency
2. **Embedding Generation**: CPU-bound for large documents
3. **Vector Search**: Linear with corpus size
4. **Memory**: Embedding model + vector store in RAM

## Troubleshooting Guide

### Common Issues

1. **High Latency**:
   - Check OpenAI API status
   - Monitor CPU usage
   - Reduce chunk retrieval count

2. **Memory Issues**:
   - Reduce chunk size
   - Use smaller embedding model
   - Increase container memory limit

3. **Connection Errors**:
   - Verify Docker network
   - Check service health
   - Review logs: `docker-compose logs`

---

**Architecture Version**: 1.0  
**Last Updated**: October 2025
