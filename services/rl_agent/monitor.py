#!/usr/bin/env python3
"""
RL Agent Monitor - Dashboard for tracking RL agent performance
"""
import time
import requests
import json
from datetime import datetime

RL_AGENT_URL = "http://localhost:5000"
API_GATEWAY_URL = "http://localhost:8000"

def print_banner():
    print("=" * 70)
    print("  RL AGENT PERFORMANCE MONITOR")
    print("=" * 70)

def get_agent_stats():
    """Get RL agent statistics"""
    try:
        response = requests.get(f"{RL_AGENT_URL}/stats", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_prometheus_metric(query):
    """Query Prometheus for a metric"""
    try:
        response = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": query},
            timeout=2
        )
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])
    except:
        pass
    return None

def monitor_loop():
    """Main monitoring loop"""
    print_banner()
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    iteration = 0
    while True:
        iteration += 1
        
        # Get agent stats
        stats = get_agent_stats()
        
        # Get system metrics
        rps = get_prometheus_metric('rate(api_gateway_queries_total[1m])')
        avg_latency = get_prometheus_metric(
            'rate(api_gateway_query_latency_seconds_sum[1m]) / '
            'rate(api_gateway_query_latency_seconds_count[1m])'
        )
        
        # Print dashboard
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}", end="")
        print(" " * 50, end="")  # Clear line
        
        if stats:
            print(f"\n┌─ RL Agent Stats " + "─" * 50)
            print(f"│ Epsilon (exploration): {stats.get('epsilon', 'N/A'):.4f}")
            print(f"│ Training steps: {stats.get('steps_done', 'N/A')}")
            print(f"│ Buffer size: {stats.get('buffer_size', 'N/A')}")
            print(f"│ Avg recent reward: {stats.get('avg_recent_reward', 'N/A'):.3f}")
            print(f"│ Device: {stats.get('device', 'N/A')}")
            print(f"└" + "─" * 68)
        
        if rps is not None or avg_latency is not None:
            print(f"┌─ System Performance " + "─" * 46)
            print(f"│ Requests/sec: {rps if rps else 'N/A':.2f}" if rps else "│ Requests/sec: N/A")
            latency_ms = (avg_latency * 1000) if avg_latency else None
            print(f"│ Avg latency: {latency_ms:.1f}ms" if latency_ms else "│ Avg latency: N/A")
            print(f"└" + "─" * 68)
        
        print("\n" + "─" * 70)
        print("Press Ctrl+C to exit\n")
        
        time.sleep(5)

def trigger_training():
    """Manually trigger training"""
    print("Triggering training...")
    try:
        response = requests.post(
            f"{RL_AGENT_URL}/train",
            params={"batch_size": 64, "iterations": 10},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Training complete:")
            print(f"  Loss: {result.get('loss', 'N/A')}")
            print(f"  Epsilon: {result.get('epsilon', 'N/A'):.4f}")
            print(f"  Buffer size: {result.get('buffer_size', 'N/A')}")
        else:
            print(f"✗ Training failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

def save_model():
    """Save model checkpoint"""
    print("Saving model...")
    try:
        response = requests.post(f"{RL_AGENT_URL}/save_model", timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Model saved to: {result.get('path', 'N/A')}")
        else:
            print(f"✗ Save failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "train":
            trigger_training()
        elif command == "save":
            save_model()
        elif command == "monitor":
            monitor_loop()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python monitor.py [monitor|train|save]")
    else:
        monitor_loop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
