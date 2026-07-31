from typing import List, Dict, Any
from services.vector_store import get_vector_store
from db.neo4j_client import get_neo4j_client

def vector_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve semantically similar chunks using FAISS."""
    vsm = get_vector_store()
    if not vsm.vector_store:
        print("Warning: Vector store not initialized. Cannot perform vector search.")
        return []
        
    results = vsm.vector_store.similarity_search_with_score(query, k=top_k)
    
    formatted_results = []
    for doc, score in results:
        formatted_results.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)  # Lower is usually better in distance metrics, depends on metric
        })
    return formatted_results

def graph_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant entities and their 1-hop relationships using full-text index."""
    client = get_neo4j_client()
    
    # We use fuzzy matching in the query by adding ~ if we want, or just basic terms
    # Using AND operator for terms is often better, but let's stick to basic keyword query
    cypher_query = """
    CALL db.index.fulltext.queryNodes("entity_name_index", $query) YIELD node, score
    MATCH path=(node)-[*1..3]-(neighbor:Entity)
    WITH path, score
    ORDER BY score DESC LIMIT $limit
    RETURN 
        [n IN nodes(path) | COALESCE(n.name, "Unknown") + " [" + COALESCE(n.type, "Unknown") + "]"] AS node_names,
        [r IN relationships(path) | type(r)] AS rel_names,
        score
    """
    
    # Simple sanitization to remove special characters that might break fulltext query parser
    safe_query = ''.join(e for e in query if e.isalnum() or e.isspace())
    
    if not safe_query.strip():
        return []
        
    formatted_results = []
    with client.driver.session() as session:
        result = session.run(cypher_query, {"query": safe_query, "limit": top_k * 5})
        
        for record in result:
            node_names = record["node_names"]
            rel_names = record["rel_names"]
            
            # Construct path string in Python
            path_parts = [f"({node_names[0]})"]
            for i, rel in enumerate(rel_names):
                path_parts.append(f"-[{rel}]-")
                path_parts.append(f"({node_names[i+1]})")
                
            path_string = " ".join(path_parts)
            
            formatted_results.append({
                "path_string": path_string,
                "score": record["score"]
            })
            
    return formatted_results

def hybrid_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Perform both vector and graph searches and combine results."""
    vector_results = vector_search(query, top_k=top_k)
    graph_results = graph_search(query, top_k=top_k)
    
    return {
        "vector_results": vector_results,
        "graph_results": graph_results
    }

def assemble_context(hybrid_results: Dict[str, Any]) -> str:
    """Format hybrid search results into a clean string for the LLM."""
    context_parts = []
    
    vector_res = hybrid_results.get("vector_results", [])
    if vector_res:
        context_parts.append("### Semantic Context from Documents ###")
        for i, res in enumerate(vector_res):
            source = res["metadata"].get("source", "Unknown")
            page = res["metadata"].get("page_number", "?")
            context_parts.append(f"Source: {source} (Page {page})\nText: {res['text']}\n")
            
    graph_res = hybrid_results.get("graph_results", [])
    if graph_res:
        context_parts.append("### Relational Context from Knowledge Graph (Multi-Hop Paths) ###")
        # Deduplicate paths for cleaner context
        paths_set = set()
        for res in graph_res:
            paths_set.add(res["path_string"])
            
        for path in paths_set:
            context_parts.append(path)
            
    if not context_parts:
        return "No relevant context found."
        
    return "\n".join(context_parts)
