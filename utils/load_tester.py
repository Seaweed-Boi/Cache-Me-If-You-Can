"""
Load Tester - Sends 50 concurrent requests to API Gateway and calculates P99 latency
"""
import os
import time
import asyncio
import statistics
import httpx

# API Gateway URL
API_URL = os.getenv("API_URL", "http://localhost:8001/query")
CONCURRENCY = int(os.getenv("LT_CONCURRENCY", 50))

# Sample queries for testing
SAMPLE_QUERIES = [
    "What is recursion in computer science?",
    "Explain the difference between REST and GraphQL.",
    "How does machine learning improve RAG systems?",
    "What are the benefits of microservices architecture?",
    "Describe the role of embeddings in vector databases.",
    "What is the CAP theorem in distributed systems?",
    "How does Redis handle persistence?",
    "Explain the difference between SQL and NoSQL databases.",
]


async def send_query(client: httpx.AsyncClient, query: str, request_id: int):
    """Send a single query and measure latency"""
    start = time.time()
    try:
        response = await client.post(
            API_URL,
            json={"query": query},
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        latency = time.time() - start
        return {
            "success": True,
            "latency": latency,
            "response": data,
            "error": None,
            "request_id": request_id
        }
    except Exception as e:
        latency = time.time() - start
        return {
            "success": False,
            "latency": latency,
            "response": None,
            "error": str(e),
            "request_id": request_id
        }


async def run_load_test(concurrency: int = CONCURRENCY):
    """
    Run load test with specified concurrency
    
    Args:
        concurrency: Number of concurrent requests (default 50)
    """
    print(f"\n{'='*60}")
    print(f"RAG System Load Test")
    print(f"{'='*60}")
    print(f"Target: {API_URL}")
    print(f"Concurrency: {concurrency} requests")
    print(f"Starting test...\n")
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # Create concurrent tasks
        tasks = [
            send_query(client, SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)], i)
            for i in range(concurrency)
        ]
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if not successful:
        print("\n❌ All requests failed!")
        print(f"Sample errors: {[r['error'] for r in failed[:3]]}")
        return
    
    # Calculate latency statistics (in milliseconds)
    latencies_ms = [r["latency"] * 1000 for r in successful]
    latencies_ms.sort()
    
    # Calculate percentiles
    p50 = statistics.median(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=100)[94] if len(latencies_ms) >= 100 else statistics.quantiles(latencies_ms, n=20)[18]
    p99 = statistics.quantiles(latencies_ms, n=100)[98] if len(latencies_ms) >= 100 else max(latencies_ms)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"Load Test Results")
    print(f"{'='*60}")
    print(f"Total Duration:    {total_time:.2f}s")
    print(f"Total Requests:    {concurrency}")
    print(f"Successful:        {len(successful)} ({len(successful)/concurrency*100:.1f}%)")
    print(f"Failed:            {len(failed)} ({len(failed)/concurrency*100:.1f}%)")
    print(f"\nLatency Statistics (ms):")
    print(f"  Min:             {min(latencies_ms):.2f}")
    print(f"  P50 (Median):    {p50:.2f}")
    print(f"  P95:             {p95:.2f}")
    print(f"  P99:             {p99:.2f}")
    print(f"  Max:             {max(latencies_ms):.2f}")
    print(f"  Average:         {statistics.mean(latencies_ms):.2f}")
    print(f"\nThroughput:        {concurrency/total_time:.2f} req/s")
    
    if failed:
        print(f"\n⚠️  Errors encountered:")
        for i, r in enumerate(failed[:5], 1):
            print(f"  {i}. [{r['request_id']}] {r['error']}")
        if len(failed) > 5:
            print(f"  ... and {len(failed) - 5} more")
    
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    asyncio.run(run_load_test())
