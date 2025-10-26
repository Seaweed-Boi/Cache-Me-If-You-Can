# Quick Reference: Running on Separate Servers

This is a quick reference for deploying Locust and Prometheus on different servers. For detailed instructions, see [SEPARATE_SERVERS_GUIDE.md](SEPARATE_SERVERS_GUIDE.md).

## Files Overview

- **docker-compose.yml** - Main RAG application (no Locust/Prometheus)
- **docker-compose.locust.yml** - Locust load testing (separate server)
- **docker-compose.prometheus.yml** - Prometheus monitoring (separate server)
- **prometheus.remote.yml** - Prometheus config template for remote monitoring
- **deploy-separate.sh** - Interactive deployment script

## Quick Start

### Option 1: Interactive Script

```bash
./deploy-separate.sh
```

This will show a menu to deploy each service.

### Option 2: Manual Deployment

#### On RAG App Server:
```bash
docker-compose up -d
# App: http://localhost:8000
# Metrics: http://localhost:8000/metrics
```

#### On Prometheus Server:
```bash
# Edit prometheus.yml to set RAG server IP
cp prometheus.remote.yml prometheus.yml
nano prometheus.yml  # Update 'your-rag-server-ip:8000'

docker-compose -f docker-compose.prometheus.yml up -d
# Prometheus: http://localhost:9090
```

#### On Locust Server:
```bash
export RAG_APP_HOST=http://your-rag-server:8000
docker-compose -f docker-compose.locust.yml up -d
# Locust: http://localhost:8089
```

## Network Requirements

Ensure these ports are accessible:

| From | To | Port | Purpose |
|------|-----|------|---------|
| Prometheus Server | RAG App Server | 8000 | Scrape metrics |
| Locust Server | RAG App Server | 8000 | Load testing |
| Your browser | Prometheus Server | 9090 | Prometheus UI |
| Your browser | Locust Server | 8089 | Locust UI |

## Verify Setup

1. **RAG App**: `curl http://<rag-server>:8000/metrics`
2. **Prometheus**: Check targets at `http://<prometheus-server>:9090/targets`
3. **Locust**: Open `http://<locust-server>:8089` and start a test

## Troubleshooting

**Prometheus can't scrape metrics?**
- Check firewall allows port 8000 from Prometheus server
- Verify RAG app is running: `curl http://<rag-server>:8000/`
- Check Prometheus config has correct IP

**Locust can't connect?**
- Verify RAG_APP_HOST environment variable
- Test connectivity: `curl http://<rag-server>:8000/`
- Check firewall rules

For more details, see [SEPARATE_SERVERS_GUIDE.md](SEPARATE_SERVERS_GUIDE.md).
