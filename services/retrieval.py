from typing import List, Dict, Any
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from services.vector_store import get_vector_store
from db.neo4j_client import get_neo4j_client
from core.config import settings
from services.extraction import get_llm

def vector_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve semantically similar chunks using FAISS with deduplication."""
    vsm = get_vector_store()
    if not vsm.vector_store:
        print("Warning: Vector store not initialized. Cannot perform vector search.")
        return []
        
    results = vsm.vector_store.similarity_search_with_score(query, k=top_k)
    
    formatted_results = []
    seen_texts = set()
    
    for doc, score in results:
        if doc.page_content not in seen_texts:
            seen_texts.add(doc.page_content)
            formatted_results.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)  # Lower is usually better in distance metrics, depends on metric
            })
    return formatted_results

def graph_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant entities and their relationships using schema-aware GraphCypherQAChain."""
    try:
        llm = get_llm()
    except Exception as e:
        print(f"Skipping graph search: {e}")
        return []

    # Connect to Neo4j graph for LangChain to fetch the exact schema dynamically
    try:
        graph = Neo4jGraph(
            url=settings.NEO4J_URI,
            username=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            refresh_schema=False
        )
        
        # Manually fetch relationship types to completely bypass the APOC plugin requirement
        client = get_neo4j_client()
        with client.driver.session() as session:
            rels_result = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS rels")
            rels = rels_result.single()["rels"]
            
        rel_paths = [f"(:Entity)-[:{rel}]->(:Entity)" for rel in rels]
        
        # Manually set the schema string that the GraphCypherQAChain expects
        graph.schema = (
            "Node properties are the following:\n"
            "Entity {name: STRING, type: STRING}\n"
            "Relationship properties are the following:\n"
            "\n"
            "The relationships are the following:\n"
            f"{', '.join(rel_paths)}\n"
        )
    except Exception as e:
        print(f"Could not connect Neo4jGraph for CypherQAChain: {e}")
        return []

    CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
You MUST follow these CRITICAL rules. If you do not, the query will fail.
1. ALWAYS use the `Entity` label for ALL nodes. NEVER use specific node labels like `:Disease`, `:Medicine`, `:RiskFactor`.
2. NEVER invent relationship types. You MUST ONLY use the EXACT relationship types provided in the schema. (e.g., use `[:COMORBID_WITH]` instead of `[:HAS_COMORBIDITY]`, and `[:TREATED_BY]` instead of `[:HAS_TREATMENT]`).
3. Filter the category of an entity using the `type` property. (e.g. `MATCH (a:Entity {{type: 'Disease'}})-...`)
4. ALWAYS use `toLower()` for case-insensitive matching on names to avoid missing data. (e.g. `MATCH (a:Entity) WHERE toLower(a.name) CONTAINS toLower('Obesity')`)
5. Example correct query: `MATCH (a:Entity {{type: 'Disease'}})-[:HAS_RISK_FACTOR]->(b:Entity) WHERE toLower(b.name) CONTAINS toLower('Obesity') RETURN a`

Schema:
{schema}
Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.
Try to return the full paths (nodes and relationships) if possible, or just the relevant connected nodes.

The question is:
{question}"""
    
    CYPHER_GENERATION_PROMPT = PromptTemplate(
        input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
    )

    try:
        chain = GraphCypherQAChain.from_llm(
            cypher_llm=llm,
            qa_llm=llm,
            graph=graph,
            verbose=True,
            cypher_prompt=CYPHER_GENERATION_PROMPT,
            return_direct=True, # Return the graph query results directly instead of LLM summary
            allow_dangerous_requests=True,
            validate_cypher=False,
            top_k=top_k * 2
        )
        
        result = chain.invoke({"query": query})
        results_data = result.get("result", [])
        
        formatted_results = []
        if isinstance(results_data, list):
            for item in results_data:
                formatted_results.append({
                    "path_string": str(item),
                    "score": 1.0 
                })
        else:
            formatted_results.append({
                "path_string": str(results_data),
                "score": 1.0
            })
            
        return formatted_results
    except Exception as e:
        print(f"Error during graph search Cypher generation: {e}")
        return []

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
