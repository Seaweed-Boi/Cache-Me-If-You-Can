"""
Locust load testing configuration for RAG API.

This file defines load tests for the RAG application endpoints:
- /query: Question-answering endpoint
- /index: Document indexing endpoint
- /: Health check endpoint

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    
    Or in Docker Compose, it will run automatically against the rag-app service.
"""

from locust import HttpUser, task, between, events
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample queries for testing the RAG system
SAMPLE_QUERIES = [
    "What is the main topic of the document?",
    "Can you summarize the key points?",
    "What are the important findings?",
    "Explain the methodology used.",
    "What conclusions were drawn?",
    "What recommendations are provided?",
    "What are the limitations mentioned?",
    "Who are the main authors or contributors?",
    "What is the purpose of this document?",
    "What future work is suggested?",
]


class RAGUser(HttpUser):
    """
    Simulates a user interacting with the RAG API.
    
    This user will:
    - Perform health checks
    - Submit queries to the RAG system
    - Occasionally trigger indexing (less frequently)
    """
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a simulated user starts."""
        logger.info("Starting RAG load test user")
        # Perform initial health check
        self.client.get("/")
    
    @task(10)
    def query_endpoint(self):
        """
        Test the /api/query endpoint.
        
        Weight: 10 - This is the primary endpoint users will hit most often.
        """
        query = random.choice(SAMPLE_QUERIES)
        
        with self.client.post(
            "/api/query",
            json={"query": query},
            catch_response=True,
            name="/api/query"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Vector store not found - this is expected initially
                response.failure("Vector store not initialized. Run /api/index first.")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def index_endpoint(self):
        """
        Test the /api/index endpoint.
        
        Weight: 1 - Indexing happens less frequently than queries.
        This is a heavy operation, so we test it less often.
        """
        with self.client.post(
            "/api/index",
            catch_response=True,
            name="/api/index"
        ) as response:
            if response.status_code == 201:
                response.success()
                logger.info("Indexing completed successfully")
            elif response.status_code == 404:
                response.failure("Data directory not found")
            else:
                response.failure(f"Indexing failed: {response.status_code}")
    
    @task(5)
    def health_check(self):
        """
        Test the health check endpoints.
        
        Weight: 5 - Health checks happen regularly for monitoring.
        """
        # Test root health check
        with self.client.get("/", catch_response=True, name="/") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
        
        # Test API health check
        with self.client.get("/api/health", catch_response=True, name="/api/health") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"API health check failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    logger.info("=" * 60)
    logger.info("Starting RAG Application Load Test")
    logger.info(f"Target host: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    logger.info("=" * 60)
    logger.info("RAG Application Load Test Completed")
    logger.info("=" * 60)


# Alternative user class for stress testing (higher load)
class StressTestUser(HttpUser):
    """
    Aggressive user for stress testing.
    Uses shorter wait times to generate higher load.
    """
    wait_time = between(0.5, 2)
    
    @task
    def rapid_queries(self):
        """Rapidly fire queries at the system."""
        query = random.choice(SAMPLE_QUERIES)
        self.client.post("/api/query", json={"query": query})
