# RL Agent Service

Deep Q-Network (DQN) based Reinforcement Learning agent for adaptive load balancing across LLM replicas.

## Overview

The RL Agent learns optimal replica selection policies by:
- **Observing** system state (replica loads, queue depths, latencies)
- **Acting** by selecting which replica to route requests to
- **Learning** from rewards based on latency and load distribution

## Architecture

```
┌──────────────┐
│ API Gateway  │ ──► Select replica? ──┐
└──────────────┘                       │
                                       ▼
                              ┌─────────────────┐
                              │   RL Agent      │
                              │   (DQN Model)   │
                              └────────┬────────┘
                                       │
                        ┌──────────────┼──────────────┐
                        ▼              ▼              ▼
                  Replica 1      Replica 2      Replica 3
                                       │
                        ┌──────────────┘
                        │
                        ▼
              Record Experience (state, action, reward)
                        │
                        ▼
              ┌─────────────────┐
              │ Replay Buffer   │
              │ (10K samples)   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Train DQN      │
              │  (Background)   │
              └─────────────────┘
```

## State Space (10 dimensions)

1-3. **Replica loads** (0-100, current load on each replica)
4. **Queue depth** (0-100, jobs waiting in Redis queue)
5. **Average latency** (0-1, last 1 minute average)
6. **Current RPS** (0-1, requests per second)
7. **Success rate** (0-1, fraction of successful requests)
8-9. **Resource usage** (memory, CPU - normalized 0-1)
10. **Time of day** (0-1, hour/24)

## Action Space

- **Action 0**: Route to Replica 1
- **Action 1**: Route to Replica 2
- **Action 2**: Route to Replica 3

## Reward Function

```python
reward = latency_reward + load_balance_bonus

where:
  latency_reward = 1.0 - (latency_ms / 1000.0)  # Higher for lower latency
  load_balance_bonus = -0.1 * variance(replica_loads)  # Encourage balance
  failure_penalty = -10.0  # Heavy penalty for failures
```

## API Endpoints

### POST `/select_replica`
Get replica selection from RL agent

**Request:**
```json
{
  "replica_loads": [5, 3, 7],
  "queue_depth": 12,
  "recent_latency_ms": 280.5,
  "current_rps": 8.2,
  "success_rate": 0.98
}
```

**Response:**
```json
{
  "replica_idx": 1,
  "replica_name": "replica-2",
  "confidence": 0.73,
  "exploration": false
}
```

### POST `/record_experience`
Record an experience for training

**Request:**
```json
{
  "state": [5, 3, 7, 12, 0.28, 8.2, 0.98, 0.5, 0.4, 0.5],
  "action": 1,
  "latency_ms": 265.3,
  "success": true,
  "replica_loads": [5, 4, 7]
}
```

### POST `/train`
Trigger training iteration

**Query Params:**
- `batch_size`: Number of samples per batch (default: 64)
- `iterations`: Number of training iterations (default: 1)

**Response:**
```json
{
  "loss": 0.0234,
  "epsilon": 0.42,
  "buffer_size": 1523,
  "steps_done": 15230
}
```

### GET `/stats`
Get agent statistics

**Response:**
```json
{
  "epsilon": 0.42,
  "steps_done": 15230,
  "buffer_size": 1523,
  "avg_recent_reward": 0.68,
  "device": "cpu",
  "model_path": "/models/rl_agent.pth"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `PROMETHEUS_URL` | `http://prometheus:9090` | Prometheus endpoint |
| `MODEL_PATH` | `/models/rl_agent.pth` | Model checkpoint path |
| `NUM_REPLICAS` | `2` | Number of LLM replicas |
| `RL_EXPLORATION` | `true` | Enable epsilon-greedy exploration |

## Training

The agent trains continuously in the background:

1. **Experience Collection**: API Gateway records every request outcome
2. **Replay Buffer**: Stores last 10,000 experiences
3. **Batch Training**: Trains on 64-sample batches every 60 seconds
4. **Target Network Update**: Updates target network every 100 steps
5. **Model Checkpoint**: Saves model every 500 steps

## Exploration vs Exploitation

- **Epsilon-greedy policy**: With probability `epsilon`, select random action (explore)
- **Epsilon decay**: `epsilon = max(0.01, epsilon * 0.995)` after each training step
- **Production mode**: Set `RL_EXPLORATION=false` to disable exploration (pure exploitation)

## Performance Metrics

Monitor agent performance via:

```bash
# Get training stats
curl http://localhost:5000/stats

# View Prometheus metrics
# api_gateway_replica_load{replica_index="0"}
# api_gateway_query_latency_seconds
```

## Usage

### Enable RL Agent in API Gateway

Set environment variable:
```yaml
api_gateway:
  environment:
    - USE_RL_AGENT=true
    - RL_AGENT_URL=http://rl_agent:5000
```

### Disable RL Agent (fallback to heuristic)

```yaml
api_gateway:
  environment:
    - USE_RL_AGENT=false
```

### Manual Training

```bash
# Trigger 10 training iterations
curl -X POST "http://localhost:5000/train?batch_size=64&iterations=10"
```

### Save Model

```bash
curl -X POST http://localhost:5000/save_model
```

## Development

### Local Testing

```bash
cd services/rl_agent
pip install -r requirements.txt
python agent.py  # Test DQN implementation
python app.py    # Run service locally
```

### Docker Build

```bash
docker build -t rl-agent ./services/rl_agent
docker run -p 5000:5000 -e REDIS_HOST=localhost rl-agent
```

## Algorithm: Deep Q-Network (DQN)

**Key Features:**
- **Experience Replay**: Breaks correlation between consecutive experiences
- **Target Network**: Stabilizes training by using separate target Q-network
- **Epsilon-greedy**: Balances exploration vs exploitation
- **Gradient Clipping**: Prevents exploding gradients

**Network Architecture:**
```
Input (10) → Dense(128, ReLU) → Dense(128, ReLU) → Dense(128, ReLU) → Output (3)
```

**Loss Function:**
```
MSE(Q(s,a), r + γ * max_a' Q_target(s',a'))
```

## Future Enhancements

- [ ] Prioritized Experience Replay (PER)
- [ ] Dueling DQN architecture
- [ ] Multi-step returns (n-step Q-learning)
- [ ] Distributed training across multiple workers
- [ ] A/B testing framework (RL vs Heuristic)
- [ ] Auto-scaling integration (scale replicas up/down)

## References

- [Playing Atari with Deep Reinforcement Learning](https://arxiv.org/abs/1312.5602) - Original DQN paper
- [Human-level control through deep reinforcement learning](https://www.nature.com/articles/nature14236) - Nature DQN paper
