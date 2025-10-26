from fastapi import APIRouter, HTTPException
from core.retriever import Retriever
from core.generator import Generator

router = APIRouter()

retriever = Retriever()
generator = Generator()

@router.post("/index")
async def index_documents(documents: list):
    try:
        retriever.index_documents(documents)
        return {"message": "Documents indexed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_documents(query: str):
    try:
        retrieved_chunks = retriever.retrieve(query)
        response = generator.generate(retrieved_chunks)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))