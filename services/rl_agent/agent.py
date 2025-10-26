"""
Reinforcement Learning Agent for Adaptive Load Balancing and Autoscaling
Uses Deep Q-Network (DQN) to learn optimal replica selection and scaling decisions
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from collections import deque
import random
import json
import os


class DQN(nn.Module):
    """Deep Q-Network for approximating Q-values"""
    
    def __init__(self, state_size, action_size, hidden_size=128):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size)
        self.fc4 = nn.Linear(hidden_size, action_size)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        return self.fc4(x)


class ReplayBuffer:
    """Experience replay buffer for training stability"""
    
    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )
    
    def __len__(self):
        return len(self.buffer)


class RLAgent:
    """
    RL Agent for load balancing across LLM replicas
    
    State Space (10 dimensions):
        - Replica 1 load
        - Replica 2 load
        - Replica 3 load (if exists)
        - Total queue depth
        - Average latency (last 1min)
        - Current RPS
        - Success rate
        - Memory usage
        - CPU usage
        - Time of day (normalized)
    
    Action Space (3 actions):
        - Action 0: Select replica-1
        - Action 1: Select replica-2
        - Action 2: Select replica-3
    
    Reward Function:
        reward = -latency - 10*failure + load_balance_bonus
        where:
        - Lower latency → higher reward
        - Failures heavily penalized
        - Load balancing encouraged
    """
    
    def __init__(
        self,
        state_size=10,
        action_size=3,
        learning_rate=0.001,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.995,
        device=None
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Q-Networks
        self.policy_net = DQN(state_size, action_size).to(self.device)
        self.target_net = DQN(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
        self.replay_buffer = ReplayBuffer(capacity=10000)
        self.steps_done = 0
        
    def select_action(self, state, explore=True):
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: Current state vector
            explore: Whether to use exploration (set False for production)
        
        Returns:
            action: Selected action (0, 1, or 2)
        """
        if explore and random.random() < self.epsilon:
            # Exploration: random action
            return random.randrange(self.action_size)
        
        # Exploitation: best action according to policy
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay buffer"""
        self.replay_buffer.push(state, action, reward, next_state, done)
    
    def train(self, batch_size=64):
        """
        Train the agent using experience replay
        
        Returns:
            loss: Training loss (None if buffer too small)
        """
        if len(self.replay_buffer) < batch_size:
            return None
        
        # Sample batch from replay buffer
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(batch_size)
        
        # Convert to tensors
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # Compute current Q values
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Compute target Q values
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Compute loss
        loss = self.criterion(current_q_values, target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        # Clip gradients
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        self.steps_done += 1
        
        return loss.item()
    
    def update_target_network(self):
        """Update target network with policy network weights"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def save(self, path):
        """Save model checkpoint"""
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps_done': self.steps_done,
        }, path)
        print(f"Model saved to {path}")
    
    def load(self, path):
        """Load model checkpoint"""
        if not os.path.exists(path):
            print(f"No checkpoint found at {path}")
            return False
        
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.steps_done = checkpoint['steps_done']
        print(f"Model loaded from {path}")
        return True
    
    def get_stats(self):
        """Get agent statistics"""
        return {
            'epsilon': self.epsilon,
            'steps_done': self.steps_done,
            'buffer_size': len(self.replay_buffer),
            'device': str(self.device)
        }


def calculate_reward(latency_ms, success, replica_loads):
    """
    Calculate reward for a given action outcome
    
    Args:
        latency_ms: Request latency in milliseconds
        success: Whether request succeeded (True/False)
        replica_loads: List of current loads on all replicas
    
    Returns:
        reward: Scalar reward value
    """
    if not success:
        return -10.0  # Heavy penalty for failures
    
    # Normalize latency to 0-1 range (assuming 0-1000ms range)
    normalized_latency = min(latency_ms / 1000.0, 1.0)
    
    # Reward inversely proportional to latency
    latency_reward = 1.0 - normalized_latency
    
    # Load balancing bonus: penalize high variance in replica loads
    if len(replica_loads) > 1:
        load_variance = np.var(replica_loads)
        load_balance_bonus = -0.1 * load_variance
    else:
        load_balance_bonus = 0.0
    
    # Combined reward
    reward = latency_reward + load_balance_bonus
    
    return reward


if __name__ == "__main__":
    # Test the agent
    agent = RLAgent(state_size=10, action_size=3)
    
    # Simulate training
    for episode in range(100):
        state = np.random.rand(10)
        action = agent.select_action(state)
        reward = np.random.randn()
        next_state = np.random.rand(10)
        
        agent.remember(state, action, reward, next_state, False)
        loss = agent.train(batch_size=32)
        
        if episode % 10 == 0:
            agent.update_target_network()
            stats = agent.get_stats()
            print(f"Episode {episode}: Loss={loss}, Epsilon={stats['epsilon']:.3f}")
    
    print("\nAgent test completed successfully!")
