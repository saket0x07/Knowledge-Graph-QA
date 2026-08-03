from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from db.neo4j_client import get_neo4j_client

router = APIRouter(prefix="/graph", tags=["Graph Visualization"])

@router.get("/visualize/{filename}", summary="Get graph nodes and edges for a specific document", response_model=Dict[str, Any])
async def visualize_graph(filename: str):
    """
    Returns nodes and edges associated with a specific uploaded document.
    Suitable for frontend visualization libraries like vis-network.
    """
    try:
        client = get_neo4j_client()
        
        # Cypher query to get the document, its chunks, and any entities/relationships extracted from those chunks.
        query = """
        MATCH (d:Document {filename: $filename})-[:HAS_CHUNK]->(c:Chunk)
        
        // Match entities connected to these chunks
        OPTIONAL MATCH (c)-[:MENTIONS]->(e1:Entity)
        OPTIONAL MATCH (c)-[:MENTIONS]->(e2:Entity)
        OPTIONAL MATCH (e1)-[r]->(e2)
        
        RETURN d, c, e1, r, e2
        """
        
        results, summary, keys = client.driver.execute_query(query, {"filename": filename})
        
        nodes = {}
        edges = []
        
        for record in results:
            # Add Document Node
            d = record.get("d")
            if d and d.get("id") not in nodes:
                nodes[d["id"]] = {"id": d["id"], "label": d["filename"], "group": "Document"}
                
            # Add Chunk Node and edge to Document
            c = record.get("c")
            if c:
                if c.get("chunk_id") not in nodes:
                    nodes[c["chunk_id"]] = {"id": c["chunk_id"], "label": f"Chunk {c.get('metadata', {}).get('page_number', '?')}", "group": "Chunk"}
                
                # Edge Document -> Chunk
                if d:
                    edges.append({"from": d["id"], "to": c["chunk_id"], "label": "HAS_CHUNK"})
                    
            # Add Entity 1 and edge from Chunk
            e1 = record.get("e1")
            if e1 and e1.get("id"):
                if e1["id"] not in nodes:
                    nodes[e1["id"]] = {"id": e1["id"], "label": e1.get("name", "Unknown"), "group": e1.get("type", "Entity")}
                
                if c:
                    edges.append({"from": c["chunk_id"], "to": e1["id"], "label": "MENTIONS"})
                    
            # Add Entity 2 and specific extracted relationship between e1 and e2
            e2 = record.get("e2")
            r = record.get("r")
            
            if e2 and e2.get("id"):
                if e2["id"] not in nodes:
                    nodes[e2["id"]] = {"id": e2["id"], "label": e2.get("name", "Unknown"), "group": e2.get("type", "Entity")}
                    
                if c:
                    edges.append({"from": c["chunk_id"], "to": e2["id"], "label": "MENTIONS"})
                
                if e1 and r:
                    edges.append({"from": e1["id"], "to": e2["id"], "label": type(r).__name__})

        # Deduplicate edges based on from, to, and label
        unique_edges = []
        seen = set()
        for edge in edges:
            identifier = f"{edge['from']}-{edge['label']}-{edge['to']}"
            if identifier not in seen:
                seen.add(identifier)
                unique_edges.append(edge)

        # To avoid massive cluttered graphs, limit nodes/edges to display if it's too big, 
        # or filter out chunks for a cleaner "knowledge-only" view. 
        # For now, return everything.
        
        return {
            "nodes": list(nodes.values()),
            "edges": unique_edges
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
