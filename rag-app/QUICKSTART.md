# Observable RAG Application - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

This guide will help you get the complete RAG application stack running with monitoring and load testing.

## Prerequisites Checklist

- [ ] Docker and Docker Compose installed
- [ ] OpenAI API key
- [ ] PDF documents to index (optional for testing)

## Step-by-Step Setup

### 1. Configure Environment

```bash
# Navigate to project directory
cd /Users/piyushshiv/Documents/rag-app

# Create .env file from template
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
# Set: OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. Add Sample Documents (Optional)

```bash
# Create data directory
mkdir -p data

# Add your PDF files
cp ~/Downloads/*.pdf data/

# Or create a sample text file for testing
echo "This is a sample document about artificial intelligence and machine learning." > data/sample.txt
```

### 3. Launch the Complete Stack

```bash
# Start all services with Docker Compose
docker-compose up -d

# Wait for services to initialize (30-60 seconds)
sleep 60

# Check status
docker-compose ps
```

Expected output:
```
NAME         IMAGE                    STATUS         PORTS
locust       locustio/locust:latest  Up             0.0.0.0:8089->8089/tcp
prometheus   prom/prometheus:latest   Up             0.0.0.0:9090->9090/tcp
rag-app      rag-app                  Up (healthy)   0.0.0.0:8000->8000/tcp
```

### 4. Verify Services

```bash
# Check RAG API health
curl http://localhost:8000/

# Check Prometheus
curl http://localhost:9090/-/healthy

# Check metrics endpoint
curl http://localhost:8000/metrics | head -20
```

### 5. Index Your Documents

```bash
# Trigger indexing (this will create the vector store)
curl -X POST http://localhost:8000/api/index
```

Expected response:
```json
{
  "message": "Indexing complete. Vector store created successfully with 150 chunks indexed."
}
```

### 6. Test a Query

```bash
# Ask a question
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
```

Expected response:
```json
{
  "answer": "Based on the provided context, this document discusses..."
}
```

## 📊 Access the Services

Open these URLs in your browser:

1. **RAG API Documentation**: http://localhost:8000/docs
   - Interactive API playground
   - Try out endpoints directly

2. **Prometheus Dashboard**: http://localhost:9090
   - View metrics and create graphs
   - Try query: `rate(http_requests_total[5m])`

3. **Locust Load Testing**: http://localhost:8089
   - Real-time performance stats
   - Adjust load and view charts

4. **Metrics Endpoint**: http://localhost:8000/metrics
   - Raw Prometheus metrics
   - Auto-scraped by Prometheus

## 🧪 Testing the Complete System

### 1. API Testing with curl

```bash
# Health check
curl http://localhost:8000/

# Query with different questions
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize the key points"}'

# Re-index if you add new documents
curl -X POST http://localhost:8000/api/index
```

### 2. Monitoring with Prometheus

Visit http://localhost:9090/graph and try these queries:

```promql
# Total requests
http_requests_total

# Request rate (requests per second)
rate(http_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Requests currently being processed
http_requests_inprogress

# Error rate
rate(http_requests_total{status="5xx"}[5m])
```

### 3. Load Testing with Locust

1. Open http://localhost:8089
2. Locust is already running with default settings:
   - 10 users
   - 2 users spawned per second
3. View real-time statistics:
   - Requests per second
   - Response times (min, max, median, 95th percentile)
   - Failure rate
4. Adjust load:
   - Click "Edit" to change user count
   - Increase to find breaking points

## 🔍 Monitoring Metrics Explained

### Key Metrics to Watch

1. **http_requests_total**
   - Total number of requests by endpoint and status code
   - Track API usage patterns

2. **http_request_duration_seconds**
   - Request processing time histogram
   - Monitor performance degradation

3. **http_requests_inprogress**
   - Currently active requests
   - Identify bottlenecks

4. **process_cpu_seconds_total**
   - CPU usage by the application
   - Detect resource constraints

## 🛠️ Troubleshooting

### Issue: "Vector store not found"

**Solution**: Run indexing first
```bash
curl -X POST http://localhost:8000/api/index
```

### Issue: "No PDF files found in ./data"

**Solution**: Add PDF files to the data directory
```bash
ls data/*.pdf  # Check if files exist
cp ~/Documents/*.pdf data/  # Add files
```

### Issue: Services won't start

**Solution**: Check logs and rebuild
```bash
# View logs
docker-compose logs rag-app
docker-compose logs prometheus
docker-compose logs locust

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: High response times

**Causes & Solutions**:
1. **First query is slow**: Embedding model needs to load (normal)
2. **Too many chunks**: Reduce `k` in retriever settings
3. **Large documents**: Adjust chunk size in indexing
4. **OpenAI rate limits**: Check API quota

### Issue: Metrics not showing in Prometheus

**Solution**: Check Prometheus targets
1. Visit http://localhost:9090/targets
2. Ensure `rag-app:8000` is "UP"
3. Check docker network: `docker network inspect rag-network`

## 📈 Performance Benchmarks

Expected performance (on standard hardware):

| Endpoint | Response Time (p95) | RPS Capacity |
|----------|-------------------|--------------|
| `/` (health) | < 10ms | 1000+ |
| `/api/query` | 1-3 seconds | 10-50 |
| `/api/index` | 30-120 seconds | N/A (one-time) |
| `/metrics` | < 50ms | 100+ |

**Note**: Query times depend on:
- Number of chunks retrieved (default: 4)
- OpenAI API latency
- Document complexity

## 🎯 Next Steps

### Production Readiness

1. **Security**:
   ```bash
   # Set proper CORS origins in src/main.py
   # Use secrets management for API keys
   # Enable HTTPS with reverse proxy
   ```

2. **Scaling**:
   ```yaml
   # Add to docker-compose.yml under rag-app:
   deploy:
     replicas: 3
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

3. **Monitoring**:
   ```bash
   # Add Grafana for visualization
   # Uncomment grafana service in docker-compose.yml
   docker-compose up -d grafana
   # Access at http://localhost:3000 (admin/admin)
   ```

4. **Alerting**:
   ```yaml
   # Create alert_rules.yml for Prometheus
   # Configure Alertmanager for notifications
   ```

### Advanced Features

1. **Add more document types**:
   - Modify `src/utils/loader.py` for DOCX, TXT, etc.
   - Use LangChain's DirectoryLoader

2. **Improve retrieval**:
   - Implement hybrid search (keyword + semantic)
   - Add reranking with cross-encoders
   - Use metadata filtering

3. **Enhance monitoring**:
   - Add custom business metrics
   - Track token usage and costs
   - Monitor embedding generation time

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **LangChain Docs**: https://python.langchain.com
- **Prometheus Guide**: https://prometheus.io/docs/introduction/overview/
- **Locust Documentation**: https://docs.locust.io

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure OpenAI API key is valid
4. Check network connectivity: `docker network ls`
5. Review error messages in Locust UI

---

**Happy RAG building! 🚀**
