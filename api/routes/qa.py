from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from services.retrieval import hybrid_search, assemble_context
from services.generation import generate_answer

router = APIRouter(prefix="/qa", tags=["QA Generation"])

class AskRequest(BaseModel):
    query: str
    top_k: int = 5
    filename: Optional[str] = None

@router.post("/ask", summary="Ask a question and get an LLM-generated answer based on the knowledge graph", response_model=Dict[str, Any])
async def ask_question(request: AskRequest):
    try:
        results = hybrid_search(request.query, request.top_k, request.filename)
        
        context_str = assemble_context(results)
        
        answer = generate_answer(request.query, context_str)
        
        return {
            "query": request.query,
            "answer": answer,
            "context_used": context_str,
            "cypher_query": results.get("cypher_query", ""),
            "sources": results.get("sources", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
