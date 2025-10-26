from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from src.api.router import router


# Create the FastAPI application instance
app = FastAPI(
    title="RAG Question-Answering API",
    description="A Retrieval-Augmented Generation API for answering questions based on PDF documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware (configure as needed for your use case)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Prometheus instrumentation
# This will automatically track request metrics and expose them at /metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

# Instrument the app and expose metrics endpoint
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)

# Include the API router
app.include_router(router)


@app.get(
    "/",
    tags=["Health"],
    summary="Root health check",
    description="Simple endpoint to verify the API is running"
)
async def root():
    """
    Root endpoint - health check.
    
    Returns:
        Status message indicating the API is operational
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )