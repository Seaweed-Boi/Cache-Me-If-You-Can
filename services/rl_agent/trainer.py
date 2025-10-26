"""
Background trainer - Continuously trains the RL agent
Runs alongside the RL agent service
"""
import time
import requests
import os

RL_AGENT_URL = os.getenv("RL_AGENT_URL", "http://localhost:5000")
TRAINING_INTERVAL = int(os.getenv("TRAINING_INTERVAL", 60))  # Train every 60 seconds
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 64))
ITERATIONS = int(os.getenv("ITERATIONS", 10))

print(f"Starting RL background trainer")
print(f"RL Agent URL: {RL_AGENT_URL}")
print(f"Training interval: {TRAINING_INTERVAL}s")

while True:
    try:
        # Train the agent
        response = requests.post(
            f"{RL_AGENT_URL}/train",
            params={"batch_size": BATCH_SIZE, "iterations": ITERATIONS},
            timeout=30
        )
        
        if response.status_code == 200:
            stats = response.json()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Training complete:")
            print(f"  Loss: {stats.get('loss', 'N/A')}")
            print(f"  Epsilon: {stats.get('epsilon', 'N/A'):.4f}")
            print(f"  Buffer size: {stats.get('buffer_size', 'N/A')}")
            print(f"  Steps: {stats.get('steps_done', 'N/A')}")
        else:
            print(f"Training failed: {response.status_code}")
    
    except Exception as e:
        print(f"Training error: {e}")
    
    # Wait before next training
    time.sleep(TRAINING_INTERVAL)
