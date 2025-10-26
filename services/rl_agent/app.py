"""
RL Agent Service - FastAPI server for load balancing decisions
Provides endpoints for replica selection and model training
"""
import os
import time
import json
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import requests
from typing import List, Optional
from datetime import datetime

from agent import RLAgent, calculate_reward

app = FastAPI(title="RL Agent Service", version="1.0")

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
MODEL_PATH = os.getenv("MODEL_PATH", "/models/rl_agent.pth")
NUM_REPLICAS = int(os.getenv("NUM_REPLICAS", 2))

# Initialize RL Agent
agent = RLAgent(state_size=10, action_size=NUM_REPLICAS)

# Try to load pre-trained model
if os.path.exists(MODEL_PATH):
    agent.load(MODEL_PATH)

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class StateRequest(BaseModel):
    replica_loads: List[int]
    queue_depth: int
    recent_latency_ms: float
    current_rps: float
    success_rate: float = 1.0


class ReplicaSelection(BaseModel):
    replica_idx: int
    replica_name: str
    confidence: float
    exploration: bool


class ExperienceRequest(BaseModel):
    state: List[float]
    action: int
    latency_ms: float
    success: bool
    replica_loads: List[int]


class TrainingStats(BaseModel):
    loss: Optional[float]
    epsilon: float
    buffer_size: int
    steps_done: int


def query_prometheus(query: str):
    """Query Prometheus for metrics"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])
        return 0.0
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
        return 0.0


def get_current_state():
    """
    Collect current system state from Redis and Prometheus
    
    Returns:
        state: 10-dimensional state vector
    """
    # Get replica loads from Redis
    replica_loads = []
    for i in range(NUM_REPLICAS):
        load = int(redis_client.get(f"llm_load_{i}") or 0)
        replica_loads.append(load)
    
    # Pad with zeros if fewer replicas
    while len(replica_loads) < 3:
        replica_loads.append(0)
    
    # Get queue depth
    queue_depth = redis_client.llen("job:llm_in") or 0
    
    # Get metrics from Prometheus
    avg_latency = query_prometheus('rate(api_gateway_query_latency_seconds_sum[1m]) / rate(api_gateway_query_latency_seconds_count[1m])')
    current_rps = query_prometheus('rate(api_gateway_queries_total[1m])')
    
    # Get success rate (assuming failures are tracked)
    total_requests = query_prometheus('api_gateway_queries_total{status="success"}')
    success_rate = 1.0 if total_requests > 0 else 0.5
    
    # System metrics (placeholder - would query from Prometheus in production)
    memory_usage = 0.5  # Normalized 0-1
    cpu_usage = 0.4  # Normalized 0-1
    
    # Time of day (normalized 0-1)
    hour = datetime.now().hour
    time_normalized = hour / 24.0
    
    # Construct state vector
    state = replica_loads + [
        queue_depth / 100.0,  # Normalize
        avg_latency,
        current_rps / 10.0,  # Normalize
        success_rate,
        memory_usage,
        cpu_usage,
        time_normalized
    ]
    
    return np.array(state[:10])  # Ensure exactly 10 dimensions


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "rl_agent"}


@app.post("/select_replica", response_model=ReplicaSelection)
async def select_replica(request: Optional[StateRequest] = None):
    """
    Select best replica for routing using RL agent
    
    Args:
        request: Optional state information (if None, fetches from system)
    
    Returns:
        Selected replica index and metadata
    """
    # Get current state
    if request:
        # Use provided state
        state = [
            *request.replica_loads[:3],
            request.queue_depth / 100.0,
            request.recent_latency_ms / 1000.0,
            request.current_rps / 10.0,
            request.success_rate,
            0.5, 0.4, 0.5  # Placeholders for memory, cpu, time
        ]
        state = np.array(state[:10])
    else:
        # Fetch state from system
        state = get_current_state()
    
    # Select action (replica)
    # Use exploration during training, exploitation during production
    explore = os.getenv("RL_EXPLORATION", "true").lower() == "true"
    action = agent.select_action(state, explore=explore)
    
    # Get Q-values for confidence metric
    with np.errstate(all='ignore'):
        import torch
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(agent.device)
        q_values = agent.policy_net(state_tensor).cpu().detach().numpy()[0]
        confidence = float(q_values[action] / (np.sum(np.abs(q_values)) + 1e-8))
    
    return ReplicaSelection(
        replica_idx=action,
        replica_name=f"replica-{action + 1}",
        confidence=confidence,
        exploration=explore and (np.random.random() < agent.epsilon)
    )


@app.post("/record_experience")
async def record_experience(request: ExperienceRequest):
    """
    Record an experience tuple for training
    
    Args:
        request: Experience containing state, action, outcome
    """
    state = np.array(request.state)
    action = request.action
    
    # Calculate reward
    reward = calculate_reward(
        request.latency_ms,
        request.success,
        request.replica_loads
    )
    
    # Get next state
    next_state = get_current_state()
    
    # Store in replay buffer
    agent.remember(state, action, reward, next_state, done=False)
    
    # Also store in Redis for persistence
    experience = {
        "state": request.state,
        "action": action,
        "reward": reward,
        "latency_ms": request.latency_ms,
        "success": request.success,
        "timestamp": time.time()
    }
    redis_client.rpush("rl_experiences", json.dumps(experience))
    redis_client.ltrim("rl_experiences", -1000, -1)  # Keep last 1000
    
    return {"status": "recorded", "reward": reward}


@app.post("/train", response_model=TrainingStats)
async def train_agent(batch_size: int = 64, iterations: int = 1):
    """
    Train the RL agent on collected experiences
    
    Args:
        batch_size: Number of experiences per training batch
        iterations: Number of training iterations
    
    Returns:
        Training statistics
    """
    losses = []
    
    for _ in range(iterations):
        loss = agent.train(batch_size=batch_size)
        if loss is not None:
            losses.append(loss)
    
    # Update target network periodically
    if agent.steps_done % 100 == 0:
        agent.update_target_network()
    
    # Save model checkpoint
    if agent.steps_done % 500 == 0:
        agent.save(MODEL_PATH)
    
    stats = agent.get_stats()
    
    return TrainingStats(
        loss=np.mean(losses) if losses else None,
        epsilon=stats['epsilon'],
        buffer_size=stats['buffer_size'],
        steps_done=stats['steps_done']
    )


@app.get("/stats")
async def get_stats():
    """Get agent statistics and performance metrics"""
    stats = agent.get_stats()
    
    # Get recent experiences
    recent_experiences = redis_client.lrange("rl_experiences", -10, -1)
    recent_rewards = []
    for exp in recent_experiences:
        try:
            data = json.loads(exp)
            recent_rewards.append(data.get('reward', 0))
        except:
            pass
    
    return {
        **stats,
        'avg_recent_reward': np.mean(recent_rewards) if recent_rewards else 0.0,
        'model_path': MODEL_PATH,
        'num_replicas': NUM_REPLICAS
    }


@app.post("/save_model")
async def save_model():
    """Manually trigger model save"""
    agent.save(MODEL_PATH)
    return {"status": "saved", "path": MODEL_PATH}


@app.post("/reset_epsilon")
async def reset_epsilon(epsilon: float = 1.0):
    """Reset exploration rate (useful for retraining)"""
    agent.epsilon = epsilon
    return {"status": "reset", "epsilon": agent.epsilon}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
