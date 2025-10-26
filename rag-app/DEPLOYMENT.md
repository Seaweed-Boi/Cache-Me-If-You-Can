# Deployment Checklist

Complete checklist for deploying the Observable RAG Application.

## ✅ Pre-Deployment Checklist

### 1. Environment Setup
- [ ] Docker installed (version 20.10+)
- [ ] Docker Compose installed (version 2.0+)
- [ ] OpenAI API key obtained
- [ ] `.env` file created with API key
- [ ] PDF documents prepared (optional for testing)

### 2. Configuration Review
- [ ] Review `docker-compose.yml` resource limits
- [ ] Check `prometheus.yml` scrape intervals
- [ ] Verify `locustfile.py` load test parameters
- [ ] Confirm `.env` variables set correctly

### 3. Security Check
- [ ] API key not committed to Git
- [ ] CORS origins configured appropriately
- [ ] Docker network isolated
- [ ] Sensitive files in `.gitignore`

## 🚀 Deployment Steps

### Step 1: Initial Setup (5 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd rag-app

# Create environment file
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY

# Create data directory
mkdir -p data

# Add PDF documents (optional)
cp ~/Documents/*.pdf data/
```

### Step 2: Build Images (2-3 minutes)

```bash
# Build the RAG application image
docker-compose build

# Expected output:
# - Successfully built <image-id>
# - Successfully tagged rag-app:latest
```

### Step 3: Start Services (1 minute)

```bash
# Start all services in detached mode
docker-compose up -d

# Wait for services to initialize
sleep 30

# Check service status
docker-compose ps

# Expected output: All services "Up" or "Up (healthy)"
```

### Step 4: Verify Services (2 minutes)

```bash
# Test RAG API
curl http://localhost:8000/
# Expected: {"status": "ok"}

# Test Prometheus
curl http://localhost:9090/-/healthy
# Expected: Prometheus is Healthy.

# Check metrics endpoint
curl http://localhost:8000/metrics | head -5
# Expected: Prometheus metrics output

# Open in browser:
# - http://localhost:8000/docs (API documentation)
# - http://localhost:9090 (Prometheus)
# - http://localhost:8089 (Locust)
```

### Step 5: Index Documents (2-5 minutes)

```bash
# Trigger indexing
curl -X POST http://localhost:8000/api/index

# Expected response:
# {
#   "message": "Indexing complete. Vector store created successfully with X chunks indexed."
# }
```

### Step 6: Test Query (10 seconds)

```bash
# Test a query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'

# Expected response:
# {
#   "answer": "Based on the context provided..."
# }
```

## 📊 Post-Deployment Validation

### Monitoring Setup

#### Prometheus (http://localhost:9090)

1. Navigate to Status → Targets
   - [ ] `rag-api` target is UP
   - [ ] Metrics being scraped successfully

2. Test queries in Graph view:
   ```promql
   # Total requests
   http_requests_total
   
   # Request rate
   rate(http_requests_total[5m])
   
   # Response time
   histogram_quantile(0.95, http_request_duration_seconds_bucket)
   ```

#### Locust (http://localhost:8089)

1. Check Locust UI is accessible
   - [ ] Statistics tab showing data
   - [ ] Charts tab displaying graphs
   - [ ] Current users: 10 (default)

2. Verify load test is running:
   - [ ] Requests/second > 0
   - [ ] No failures (or < 1% failure rate)
   - [ ] Response times reasonable (< 5s for queries)

#### Application Logs

```bash
# View RAG application logs
docker-compose logs -f rag-app

# Expected: No ERROR level messages
# OK: INFO messages about requests
```

### Performance Validation

Run these tests to ensure proper operation:

#### 1. Health Check Performance
```bash
# Should respond in < 50ms
time curl http://localhost:8000/
```

#### 2. Query Performance
```bash
# Should respond in 1-3 seconds
time curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test question?"}'
```

#### 3. Metrics Endpoint
```bash
# Should return metrics without errors
curl http://localhost:8000/metrics | grep http_requests_total
```

#### 4. Load Test Validation
- [ ] Open http://localhost:8089
- [ ] Check "Total Requests" > 0
- [ ] Verify "Failures" < 5%
- [ ] Confirm "Median Response Time" < 3000ms

## 🔧 Troubleshooting

### Issue: Services won't start

```bash
# Check for port conflicts
lsof -i :8000
lsof -i :9090
lsof -i :8089

# View detailed logs
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Issue: "Vector store not found" error

```bash
# Ensure indexing completed
curl -X POST http://localhost:8000/api/index

# Check vector store exists
ls -la chroma_db/

# View indexing logs
docker-compose logs rag-app | grep -i index
```

### Issue: Prometheus not scraping metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Verify network connectivity
docker exec prometheus ping rag-app -c 3

# Check metrics endpoint from Prometheus container
docker exec prometheus wget -O- http://rag-app:8000/metrics
```

### Issue: High memory usage

```bash
# Check resource usage
docker stats

# Reduce chunk retrieval in src/core/qa_pipeline.py:
# search_kwargs={"k": 2}  # Instead of 4

# Restart service
docker-compose restart rag-app
```

### Issue: Slow query responses

Possible causes and solutions:

1. **First query always slow**: Normal (model loading)
2. **All queries slow**: 
   - Check OpenAI API status
   - Verify internet connection
   - Review API quota limits
3. **Too many chunks**: Reduce `k` in retriever
4. **Large documents**: Reduce chunk size in indexing

## 🎯 Production Readiness

### Required Changes for Production

#### 1. Security
```bash
# In src/main.py, update CORS:
allow_origins=["https://yourdomain.com"]

# Use secrets management:
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

#### 2. Resource Limits
```yaml
# In docker-compose.yml, add:
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

#### 3. Persistent Storage
```yaml
# Add volume for ChromaDB:
volumes:
  chroma_data:
    driver: local
```

#### 4. Monitoring Enhancements
```bash
# Uncomment Grafana in docker-compose.yml
# Add Alertmanager for notifications
# Configure Prometheus alerts
```

#### 5. Logging
```bash
# Add centralized logging:
# - ELK Stack (Elasticsearch, Logstash, Kibana)
# - Grafana Loki
# - CloudWatch Logs
```

#### 6. HTTPS/TLS
```bash
# Add reverse proxy (nginx/traefik)
# Configure SSL certificates
# Redirect HTTP to HTTPS
```

## 📈 Performance Optimization

### Before Going Live

1. **Load Testing**:
   ```bash
   # Increase Locust users to find limits
   # In Locust UI: Set to 100 users, spawn rate 10
   # Monitor response times and failure rates
   ```

2. **Optimize Chunk Size**:
   ```python
   # In src/core/indexing.py
   # Experiment with different chunk sizes:
   chunk_size=500   # Faster, less context
   chunk_size=1500  # Slower, more context
   ```

3. **Cache Frequent Queries**:
   ```python
   # Add Redis caching layer
   # Cache query results for 1 hour
   ```

4. **Upgrade LLM**:
   ```python
   # In src/core/qa_pipeline.py
   model="gpt-4"  # Better quality
   # or
   model="gpt-3.5-turbo-16k"  # More context
   ```

## ✅ Final Verification

### Pre-Launch Checklist

- [ ] All services running and healthy
- [ ] API endpoints responding correctly
- [ ] Prometheus collecting metrics
- [ ] Locust load test passing
- [ ] No critical errors in logs
- [ ] Query responses accurate
- [ ] Response times acceptable (< 5s)
- [ ] Memory usage stable
- [ ] CPU usage reasonable (< 80%)
- [ ] Documentation reviewed
- [ ] Backup strategy defined
- [ ] Rollback plan prepared

### Launch Metrics Baseline

Record these metrics before launch:

```bash
# Query response time
curl -w "@curl-format.txt" -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test"}'

# Requests per second capacity
# Check Locust UI "Statistics" tab

# Memory usage
docker stats rag-app --no-stream

# Disk usage
du -sh chroma_db/
```

## 🎉 Success Criteria

Deployment is successful when:

1. ✅ All services start without errors
2. ✅ Health checks pass consistently
3. ✅ Query endpoint returns accurate answers
4. ✅ Prometheus shows metrics flowing
5. ✅ Locust tests pass with < 5% failure rate
6. ✅ Response times meet requirements
7. ✅ No memory leaks observed
8. ✅ Documentation is complete

## 📞 Support Resources

- **Application Logs**: `docker-compose logs -f`
- **Prometheus Metrics**: http://localhost:9090
- **API Documentation**: http://localhost:8000/docs
- **Architecture Guide**: See ARCHITECTURE.md
- **Quick Start Guide**: See QUICKSTART.md

---

**Good luck with your deployment! 🚀**
