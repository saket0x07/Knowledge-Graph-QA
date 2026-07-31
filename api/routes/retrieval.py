from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, Optional
from enum import Enum

from services.retrieval import vector_search, graph_search, hybrid_search, assemble_context

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

class SearchMode(str, Enum):
    vector = "vector"
    graph = "graph"
    hybrid = "hybrid"

@router.get("/search", summary="Search knowledge base", response_model=Dict[str, Any])
async def search(
    query: str = Query(..., description="The search query"),
    mode: SearchMode = Query(SearchMode.hybrid, description="Search mode: vector, graph, or hybrid"),
    top_k: int = Query(5, description="Number of top results to retrieve"),
    include_context: bool = Query(True, description="Whether to include the assembled string context in the response")
):
    try:
        results = {}
        if mode == SearchMode.vector:
            vector_res = vector_search(query, top_k)
            results = {"vector_results": vector_res}
        elif mode == SearchMode.graph:
            graph_res = graph_search(query, top_k)
            results = {"graph_results": graph_res}
        elif mode == SearchMode.hybrid:
            results = hybrid_search(query, top_k)
            
        response = {"query": query, "mode": mode.value, "results": results}
        
        if include_context:
            context_str = assemble_context(results)
            response["assembled_context"] = context_str
            
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
