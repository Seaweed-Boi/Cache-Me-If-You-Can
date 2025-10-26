# Running Locust and Prometheus on Separate Servers

This guide explains how to run Locust (load testing) and Prometheus (monitoring) on different servers from your RAG application.

## Architecture Overview

- **Server 1 (RAG App Server)**: Runs the main RAG application and Qdrant vector database
- **Server 2 (Monitoring Server)**: Runs Prometheus for metrics collection
- **Server 3 (Load Testing Server)**: Runs Locust for performance testing

## Prerequisites

- Docker and Docker Compose installed on all servers
- Network connectivity between servers (ensure firewall rules allow communication)
- The following files from this repository:
  - For RAG App Server: `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `src/`, `data/`
  - For Monitoring Server: `docker-compose.prometheus.yml`, `prometheus.remote.yml`
  - For Load Testing Server: `docker-compose.locust.yml`, `locustfile.py`

## Setup Instructions

### 1. RAG Application Server

This server runs the main application and Qdrant database.

```bash
# On the RAG app server
cd /path/to/rag-app

# Start the RAG application and Qdrant
docker-compose up -d

# Verify services are running
docker-compose ps

# Check the application is accessible
curl http://localhost:8000/
```

The RAG app will be available on:
- Application: `http://<rag-server-ip>:8000`
- Metrics endpoint: `http://<rag-server-ip>:8000/metrics`
- Qdrant: `http://<rag-server-ip>:6333`

**Important**: Note the IP address or hostname of this server for configuration in other servers.

### 2. Prometheus Monitoring Server

This server collects and stores metrics from the RAG application.

```bash
# On the monitoring server
# Copy these files to the server:
# - docker-compose.prometheus.yml
# - prometheus.remote.yml

# Edit prometheus.remote.yml to point to your RAG app server
nano prometheus.remote.yml

# Update the targets line in the 'rag-api' job:
# Replace 'your-rag-server-ip:8000' with your actual RAG server address
# Example: - targets: ['192.168.1.100:8000']
#       or - targets: ['rag-server.example.com:8000']
```

Update the Prometheus configuration:
```yaml
scrape_configs:
  - job_name: 'rag-api'
    static_configs:
      - targets: ['192.168.1.100:8000']  # Replace with your RAG server IP
        labels:
          service: 'rag-api'
          environment: 'production'
```

Start Prometheus:
```bash
# Copy the remote config as the main config
cp prometheus.remote.yml prometheus.yml

# Start Prometheus
docker-compose -f docker-compose.prometheus.yml up -d

# Verify Prometheus is running
docker-compose -f docker-compose.prometheus.yml ps

# Check Prometheus web UI
# Open http://<prometheus-server-ip>:9090 in your browser
```

Prometheus will be available at:
- Web UI: `http://<prometheus-server-ip>:9090`

**Verify the connection**:
1. Open `http://<prometheus-server-ip>:9090/targets`
2. Check that the 'rag-api' target is "UP" (green)
3. If it shows "DOWN", verify:
   - Network connectivity between servers
   - Firewall allows port 8000 from Prometheus server to RAG server
   - RAG app is running and metrics endpoint is accessible

### 3. Locust Load Testing Server

This server runs load tests against the RAG application.

```bash
# On the load testing server
# Copy these files to the server:
# - docker-compose.locust.yml
# - locustfile.py

# Set the RAG app server URL
export RAG_APP_HOST=http://192.168.1.100:8000  # Replace with your RAG server

# Start Locust
docker-compose -f docker-compose.locust.yml up -d

# Verify Locust is running
docker-compose -f docker-compose.locust.yml ps
```

Locust will be available at:
- Web UI: `http://<locust-server-ip>:8089`

**Using Locust**:
1. Open `http://<locust-server-ip>:8089` in your browser
2. Configure your load test:
   - Number of users: Start with 10-50
   - Spawn rate: 1-5 users per second
   - Host: Should already be set to your RAG app server
3. Click "Start swarming" to begin the test
4. Monitor results in real-time
5. View metrics in Prometheus/Grafana for deeper analysis

## Network Configuration

### Required Port Access

**RAG App Server** (needs to allow incoming connections):
- Port 8000: From Prometheus server (for metrics scraping)
- Port 8000: From Locust server (for load testing)
- Port 6333: (Optional) For direct Qdrant access

**Prometheus Server** (needs to allow incoming connections):
- Port 9090: From your browser/monitoring clients

**Locust Server** (needs to allow incoming connections):
- Port 8089: From your browser/testing clients

### Firewall Configuration Example (Ubuntu/Debian)

On the **RAG App Server**:
```bash
# Allow Prometheus server to access metrics
sudo ufw allow from <prometheus-server-ip> to any port 8000

# Allow Locust server to access the app
sudo ufw allow from <locust-server-ip> to any port 8000

# Or allow from any IP (less secure)
sudo ufw allow 8000/tcp
```

On the **Prometheus Server**:
```bash
sudo ufw allow 9090/tcp
```

On the **Locust Server**:
```bash
sudo ufw allow 8089/tcp
```

## Alternative: Using Environment Variables

Instead of editing configuration files, you can use environment variables:

### Locust with Environment Variables
```bash
export RAG_APP_HOST=http://your-rag-server.com:8000
docker-compose -f docker-compose.locust.yml up -d
```

### Prometheus with Environment Variables
You'll need to create a templated prometheus.yml file or use environment variable substitution:

```yaml
# prometheus.yml (using environment variables)
scrape_configs:
  - job_name: 'rag-api'
    static_configs:
      - targets: ['${RAG_APP_HOST}']
```

Then use:
```bash
export RAG_APP_HOST=your-rag-server.com:8000
docker-compose -f docker-compose.prometheus.yml up -d
```

## Monitoring and Maintenance

### View Logs

```bash
# RAG App Server
docker-compose logs -f rag-app

# Prometheus Server
docker-compose -f docker-compose.prometheus.yml logs -f prometheus

# Locust Server
docker-compose -f docker-compose.locust.yml logs -f locust
```

### Restart Services

```bash
# RAG App Server
docker-compose restart rag-app

# Prometheus Server
docker-compose -f docker-compose.prometheus.yml restart prometheus

# Locust Server
docker-compose -f docker-compose.locust.yml restart locust
```

### Stop Services

```bash
# RAG App Server
docker-compose down

# Prometheus Server
docker-compose -f docker-compose.prometheus.yml down

# Locust Server
docker-compose -f docker-compose.locust.yml down
```

## Troubleshooting

### Prometheus Cannot Scrape Metrics

**Problem**: Prometheus shows target as "DOWN"

**Solutions**:
1. Verify RAG app is running: `curl http://<rag-server-ip>:8000/metrics`
2. Check network connectivity: `ping <rag-server-ip>` from Prometheus server
3. Test port access: `telnet <rag-server-ip> 8000` from Prometheus server
4. Check firewall rules on RAG app server
5. Verify Prometheus configuration has correct IP/hostname

### Locust Cannot Connect to RAG App

**Problem**: Locust shows connection errors

**Solutions**:
1. Verify RAG app is running: `curl http://<rag-server-ip>:8000/`
2. Check the RAG_APP_HOST environment variable
3. Verify network connectivity from Locust server
4. Check firewall rules on RAG app server

### DNS Resolution Issues

If using hostnames instead of IP addresses:
1. Ensure DNS is properly configured
2. Try using IP addresses instead
3. Add entries to `/etc/hosts` if needed:
   ```
   192.168.1.100  rag-server
   192.168.1.101  prometheus-server
   192.168.1.102  locust-server
   ```

## Best Practices

1. **Security**:
   - Use HTTPS/TLS for production deployments
   - Restrict port access with firewalls
   - Use VPN or private networks when possible
   - Enable authentication on Prometheus and Locust web UIs

2. **Performance**:
   - Keep Prometheus close to the application to reduce latency
   - Use appropriate scrape intervals (10-15s is usually fine)
   - Monitor Prometheus's own resource usage

3. **Monitoring**:
   - Set up alerts in Prometheus for critical metrics
   - Use Grafana for better visualization (can run on Prometheus server)
   - Monitor all three servers' resource usage (CPU, memory, disk)

4. **Load Testing**:
   - Start with small number of users and gradually increase
   - Monitor application metrics during load tests
   - Don't run continuous high-load tests on production systems

## Production Considerations

For production deployments, consider:

1. **High Availability**: Run multiple instances of each component
2. **Data Persistence**: Ensure Prometheus data volume is backed up
3. **Monitoring the Monitors**: Set up alerting for Prometheus itself
4. **Scaling**: Consider Prometheus federation for large-scale monitoring
5. **Security**: Implement proper authentication and encryption
6. **Resource Limits**: Set appropriate resource limits in Docker Compose

## Quick Reference

### Service URLs

| Service | Default URL | Purpose |
|---------|------------|---------|
| RAG App | http://rag-server:8000 | Main application |
| Metrics | http://rag-server:8000/metrics | Prometheus metrics |
| Qdrant | http://rag-server:6333 | Vector database |
| Prometheus | http://prometheus-server:9090 | Metrics monitoring |
| Locust | http://locust-server:8089 | Load testing UI |

### Common Commands

```bash
# Start all services on respective servers
docker-compose up -d                                    # RAG App
docker-compose -f docker-compose.prometheus.yml up -d   # Prometheus
docker-compose -f docker-compose.locust.yml up -d       # Locust

# View logs
docker-compose logs -f
docker-compose -f docker-compose.prometheus.yml logs -f
docker-compose -f docker-compose.locust.yml logs -f

# Stop all services
docker-compose down
docker-compose -f docker-compose.prometheus.yml down
docker-compose -f docker-compose.locust.yml down
```

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Verify configuration files are correctly set up
3. Ensure network connectivity between servers
4. Review firewall and security group rules
