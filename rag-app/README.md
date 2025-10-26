# RAG Application

This project is a simplified monolithic Retrieval-Augmented Generation (RAG) application built using FastAPI. It integrates document retrieval and response generation using a language model.

## Project Structure

```
rag-app
├── src
│   ├── main.py               # Entry point for the FastAPI application
│   ├── api                   # Contains API routes
│   │   ├── __init__.py
│   │   └── routes.py         # Defines API endpoints
│   ├── core                  # Core RAG logic
│   │   ├── __init__.py
│   │   ├── retriever.py      # Logic for retrieving documents
│   │   ├── generator.py      # Logic for generating responses
│   │   └── rag_pipeline.py    # Core RAG pipeline logic
│   ├── config                # Configuration settings
│   │   ├── __init__.py
│   │   └── settings.py       # Application settings
│   └── utils                 # Utility functions
│       ├── __init__.py
│       └── helpers.py        # Helper functions
├── tests                     # Unit tests
│   ├── __init__.py
│   ├── test_retriever.py     # Tests for retriever logic
│   └── test_generator.py      # Tests for generator logic
├── Dockerfile                # Docker container configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
└── README.md                 # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd rag-app
   ```

2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```
   uvicorn src.main:app --reload
   ```

## API Endpoints

- **POST /index**: Triggers the indexing process.
- **POST /query**: Handles user queries and returns generated responses.

## Dockerization

To build and run the application in a Docker container, use the following commands:

1. **Build the Docker image:**
   ```
   docker build -t rag-app .
   ```

2. **Run the Docker container:**
   ```
   docker run -p 8000:8000 rag-app
   ```

## Usage Examples

Once the application is running, you can access the API endpoints using tools like Postman or curl.

- To index documents:
  ```
  curl -X POST "http://localhost:8000/index" -H "Content-Type: application/json" -d '{"documents": ["doc1", "doc2"]}'
  ```

- To query the application:
  ```
  curl -X POST "http://localhost:8000/query" -H "Content-Type: application/json" -d '{"query": "What is RAG?"}'
  ```

## License

This project is licensed under the MIT License. See the LICENSE file for details.