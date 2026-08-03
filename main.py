from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.neo4j_client import get_neo4j_client
from db.cypher_init import init_db_schema
from db.sqlite_client import init_sqlite_db
from api.routes import documents, retrieval, qa, graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite
    init_sqlite_db()
    print("Initialized SQLite DB for ingestion history.")
    
    # Startup: Verify Neo4j connection
    client = get_neo4j_client()
    if client.verify_connectivity():
        print("Successfully connected to Neo4j!")
        # Initialize schema (constraints and indexes)
        print("Initializing Neo4j schema...")
        init_db_schema()
    else:
        print("Warning: Could not connect to Neo4j. Check if Neo4j Desktop is running.")
    yield
    # Shutdown: Close connection
    client.close()

app = FastAPI(
    title="KnowledgeGraph-RAG",
    description="Intelligent Document-to-Graph Knowledge System",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(documents.router)
app.include_router(retrieval.router)
app.include_router(qa.router)
app.include_router(graph.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
