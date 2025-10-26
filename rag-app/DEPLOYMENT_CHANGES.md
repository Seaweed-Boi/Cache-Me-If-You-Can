# Separate Server Deployment - Summary

## What Was Done

The RAG application has been reconfigured to support running Locust (load testing) and Prometheus (monitoring) on separate servers from the main application. This allows for better resource isolation and scalability.

## Files Created/Modified

### New Files Created:

1. **docker-compose.locust.yml**
   - Standalone Docker Compose file for running Locust on a separate server
   - Configured to connect to a remote RAG application
   - Uses environment variable `RAG_APP_HOST` for flexibility

2. **docker-compose.prometheus.yml**
   - Standalone Docker Compose file for running Prometheus on a separate server
   - Configured to scrape metrics from a remote RAG application
   - Includes volume for persistent metric storage

3. **prometheus.remote.yml**
   - Prometheus configuration template for remote monitoring
   - Contains placeholders for RAG server IP/hostname
   - Ready to be customized for your deployment

4. **deploy-separate.sh**
   - Interactive bash script for easy deployment
   - Menu-driven interface for deploying/managing services
   - Automatically configures server addresses

5. **SEPARATE_SERVERS_GUIDE.md**
   - Comprehensive guide (9.9KB) covering:
     - Architecture overview
     - Step-by-step setup instructions for each server
     - Network configuration and firewall rules
     - Troubleshooting common issues
     - Best practices and production considerations

6. **SEPARATE_SERVERS_QUICKSTART.md**
   - Quick reference guide (2.3KB)
   - Fast deployment instructions
   - Common commands and troubleshooting

7. **.env.separate.example**
   - Environment variable template
   - Documents all configuration options
   - Includes examples and notes

### Modified Files:

1. **docker-compose.yml**
   - Removed Prometheus service
   - Removed Locust service
   - Removed prometheus-data volume
   - Now only contains RAG app and Qdrant
   - Cleaner, focused on core application

## Architecture

### Before (All-in-One):
```
┌─────────────────────────────────────┐
│        Single Server                │
│  ┌──────────┐  ┌──────────────┐    │
│  │ RAG App  │  │  Qdrant      │    │
│  └──────────┘  └──────────────┘    │
│  ┌──────────┐  ┌──────────────┐    │
│  │Prometheus│  │   Locust     │    │
│  └──────────┘  └──────────────┘    │
└─────────────────────────────────────┘
```

### After (Distributed):
```
┌────────────────┐    ┌──────────────────┐    ┌────────────────┐
│  RAG Server    │◄───│ Prometheus Server│    │ Locust Server  │
│                │    │                  │    │                │
│ ┌────────────┐ │    │ ┌──────────────┐ │    │ ┌────────────┐ │
│ │  RAG App   │ │    │ │  Prometheus  │ │    │ │   Locust   │ │
│ └────────────┘ │    │ └──────────────┘ │    │ └────────────┘ │
│ ┌────────────┐ │    │   (Scrapes       │    │   (Tests       │
│ │  Qdrant    │ │    │    metrics)      │    │    RAG API)    │
│ └────────────┘ │    │                  │    │                │
└────────────────┘    └──────────────────┘    └────────────────┘
     :8000                  :9090                   :8089
```

## Benefits

1. **Resource Isolation**: Each service can have dedicated resources
2. **Scalability**: Easier to scale individual components
3. **Flexibility**: Run services on different infrastructure
4. **Security**: Better network segmentation
5. **Maintenance**: Update/restart services independently

## Deployment Options

### Option 1: All on One Server (Original Setup)
```bash
# Use the original setup with everything together
docker-compose up -d
```

### Option 2: Separate Servers (New Setup)

**Server 1 (RAG App):**
```bash
docker-compose up -d
```

**Server 2 (Prometheus):**
```bash
# Update prometheus.yml with RAG server IP
docker-compose -f docker-compose.prometheus.yml up -d
```

**Server 3 (Locust):**
```bash
export RAG_APP_HOST=http://rag-server:8000
docker-compose -f docker-compose.locust.yml up -d
```

### Option 3: Using the Interactive Script
```bash
./deploy-separate.sh
```

## Next Steps

1. **For Testing Locally**: Just use the new files to test the separation
2. **For Production Deployment**: 
   - Follow the [SEPARATE_SERVERS_GUIDE.md](SEPARATE_SERVERS_GUIDE.md)
   - Configure firewalls and network access
   - Update server addresses in configuration files
   - Deploy each service on its designated server

## Quick Test

To test the new setup locally (simulating separate servers):

1. Start RAG app:
   ```bash
   docker-compose up -d
   ```

2. In a new terminal, start Prometheus:
   ```bash
   # Update prometheus.yml to use 'host.docker.internal:8000' for Mac/Windows
   # or your machine's IP for Linux
   docker-compose -f docker-compose.prometheus.yml up -d
   ```

3. In another terminal, start Locust:
   ```bash
   export RAG_APP_HOST=http://host.docker.internal:8000  # Mac/Windows
   # or export RAG_APP_HOST=http://172.17.0.1:8000  # Linux
   docker-compose -f docker-compose.locust.yml up -d
   ```

4. Access services:
   - RAG App: http://localhost:8000
   - Prometheus: http://localhost:9090
   - Locust: http://localhost:8089

## Support

For detailed instructions, troubleshooting, and best practices, refer to:
- [SEPARATE_SERVERS_GUIDE.md](SEPARATE_SERVERS_GUIDE.md) - Complete guide
- [SEPARATE_SERVERS_QUICKSTART.md](SEPARATE_SERVERS_QUICKSTART.md) - Quick reference

## Files Summary

| File | Size | Purpose |
|------|------|---------|
| docker-compose.yml | 2.0KB | Main RAG app (updated) |
| docker-compose.locust.yml | 1.2KB | Locust deployment |
| docker-compose.prometheus.yml | 1.2KB | Prometheus deployment |
| prometheus.remote.yml | 1.6KB | Prometheus config template |
| deploy-separate.sh | 5.1KB | Interactive deployment script |
| SEPARATE_SERVERS_GUIDE.md | 9.9KB | Comprehensive guide |
| SEPARATE_SERVERS_QUICKSTART.md | 2.3KB | Quick reference |
| .env.separate.example | 1.6KB | Environment variables template |

Total documentation: ~25KB of guides and configurations
