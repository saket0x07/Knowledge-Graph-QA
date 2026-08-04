# Comprehensive Codebase & Architecture Guide: KnowledgeGraph-RAG

Welcome to the **KnowledgeGraph-RAG** codebase! This guide is written specifically for developers new to the project. It explains the entire architecture, design patterns, data flow, and file sequence from environment initialization to final answer generation.

Follow this document file by file in sequence to get a complete, deep understanding of how every component operates.

---

## Table of Contents
1. [Architecture Overview & Data Flow](#1-architecture-overview--data-flow)
2. [Step 1: Configuration & Environment (`core/config.py`, `.env`)](#step-1-configuration--environment-coreconfigpy-env)
3. [Step 2: Database Connections & Schema (`db/neo4j_client.py`, `db/cypher_init.py`, `db/sqlite_client.py`)](#step-2-database-connections--schema-dbneo4j_clientpy-dbcypher_initpy-dbsqlite_clientpy)
4. [Step 3: Data Schemas & Models (`models/schema.py`)](#step-3-data-schemas--models-modelsschemapy)
5. [Step 4: FastAPI Entrypoint & Application Lifespan (`main.py`)](#step-4-fastapi-entrypoint--application-lifespan-mainpy)
6. [Step 5: Document Upload & Ingestion Engine (`api/routes/documents.py`, `utils/parsers.py`, `services/ingestion.py`)](#step-5-document-upload--ingestion-engine-apiroutesdocumentspy-utilsparserspy-servicesingestionpy)
7. [Step 6: Dynamic Entity Extraction & Knowledge Graph Construction (`services/extraction.py`, `services/graph_builder.py`)](#step-6-dynamic-entity-extraction--knowledge-graph-construction-servicesextractionpy-servicesgraph_builderpy)
8. [Step 7: Hybrid Vector Store (`services/vector_store.py`)](#step-7-hybrid-vector-store-servicesvector_storepy)
9. [Step 8: Retrieval Engine & Cypher Query Generation (`services/retrieval.py`, `api/routes/retrieval.py`)](#step-8-retrieval-engine--cypher-query-generation-servicesretrievalpy-apiroutesretrievalpy)
10. [Step 9: Answer Generation & Q&A (`services/generation.py`, `api/routes/qa.py`)](#step-9-answer-generation--qa-servicesgenerationpy-apiroutesqapy)
11. [Step 10: Graph Visualization API (`api/routes/graph.py`)](#step-10-graph-visualization-api-apiroutesgraphpy)
12. [Step 11: Streamlit User Interface (`ui.py`)](#step-11-streamlit-user-interface-uipy)
13. [Sequence Summary & Cheat Sheet](#sequence-summary--cheat-sheet)

---

## 1. Architecture Overview & Data Flow

This application is an **Intelligent Document-to-Graph Knowledge RAG System**. It converts raw PDF documents into two complementary representations:
1. **Semantic Vector Index**: For similarity search over textual chunks (powered by FAISS and BAAI/bge-m3 embeddings).
2. **Relational Knowledge Graph**: For multi-hop relational reasoning over structured entities and relationships (stored in Neo4j).

```
   +-------------------+
   |   PDF Document    |
   +---------+---------+
             |
             v
   +-------------------+
   |  PyMuPDF Parser   |
   +---------+---------+
             |
             v
   +-------------------+
   |  Text Splitter    |  (RecursiveCharacterTextSplitter: size=1000, overlap=200)
   +----+---------+----+
        |         |
        v         v
 +------------+  +-----------------------------------+
 |   FAISS    |  |       Neo4j Graph Database        |
 | Vector Store|  | Document -> Chunk -> Entity -> ...|
 +------------+  +-----------------------------------+
                          ^
                          | (Extracted via LLM Async Jobs)
                  +-------+---------------+
                  | Structured LLM        |
                  | OpenRouter GPT-4o     |
                  +-----------------------+
```

---

## Step 1: Configuration & Environment (`core/config.py`, `.env`)

Every request and module relies on centralized settings managed by **Pydantic Settings**.

### Files:
- [`.env`](file:///d:/Fxis.ai/Rag's/Graph-QA/.env)
- [`core/config.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/core/config.py)

### Detailed Breakdown:
- **`.env`**: Holds environment variable overrides such as `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD`.
- **`core/config.py`**:
  ```python
  class Settings(BaseSettings):
      PROJECT_NAME: str = "KnowledgeGraph-RAG"
      NEO4J_URI: str = "bolt://localhost:7687"
      NEO4J_USER: str = "neo4j"
      NEO4J_PASSWORD: str = "password"
      OPENROUTER_API_KEY: str = ""
      OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
      model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

  settings = Settings()
  ```
- **Key Takeaway**: Importing `settings` anywhere in the project provides typed access to connection parameters and API keys loaded automatically from `.env`.

---

## Step 2: Database Connections & Schema (`db/neo4j_client.py`, `db/cypher_init.py`, `db/sqlite_client.py`)

The project uses two databases: **Neo4j Desktop** (graph database) and **SQLite** (lightweight relational log for document ingestion tracking).

### Files:
- [`db/neo4j_client.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/db/neo4j_client.py)
- [`db/cypher_init.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/db/cypher_init.py)
- [`db/sqlite_client.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/db/sqlite_client.py)

### Detailed Breakdown:

#### 1. Neo4j Client Connection (`db/neo4j_client.py`)
- Neo4j Desktop runs locally by default listening on `bolt://localhost:7687`.
- The `Neo4jClient` class initializes an official Neo4j Python `GraphDatabase.driver` using parameters from `settings`.
- `verify_connectivity()` tests the connection at server startup.
- Dependency injection function `get_neo4j_client()` exposes a singleton driver instance.

#### 2. Neo4j Schema Initialization (`db/cypher_init.py`)
At startup, `init_db_schema()` creates essential constraints and indexes to enforce uniqueness and accelerate Cypher lookups:
- `CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE`
- `CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE`
- `CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE`
- `CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)`
- `CREATE FULLTEXT INDEX chunk_text_index IF NOT EXISTS FOR (n:Chunk) ON EACH [n.text]`
- `CREATE FULLTEXT INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON EACH [e.name]`

#### 3. SQLite Local Tracking (`db/sqlite_client.py`)
- Uses thread locking (`threading.Lock()`) to manage concurrent reads and writes to `app.db`.
- Table `ingestion_history` stores `filename`, `file_size_mb`, `status` (`Processing`, `Success`, `Failed`), and `timestamp`.
- Functions `log_ingestion_start()`, `update_ingestion_status()`, and `get_ingestion_history()` keep the frontend informed of background ingestion state.

---

## Step 3: Data Schemas & Models (`models/schema.py`)

This file defines the domain objects using **Pydantic**. These models maintain strict data validation across API routes, LLM extraction chains, and database queries.

### File:
- [`models/schema.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/models/schema.py)

### Key Schemas:
- `DocumentModel`: Unique document UUID, filename, and UTC upload timestamp.
- `ChunkModel`: Unique chunk ID (`{doc_id}_p{page}_c{index}`), parent document ID, textual content, and metadata dictionary (page number, file source).
- `EntityModel`: Normalized ID (e.g. `"openai"`), display name (`"OpenAI"`), and entity type category (e.g. `"Organization"`).
- `RelationshipModel`: `source_entity_id`, `target_entity_id`, and `relation_type` (e.g. `"DEVELOPED"`).

---

## Step 4: FastAPI Entrypoint & Application Lifespan (`main.py`)

`main.py` bootstraps the web server and orchestrates startup database connections.

### File:
- [`main.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/main.py)

### Execution Flow:
1. Defines an `asynccontextmanager` called `lifespan(app: FastAPI)`:
   - On startup: Calls `init_sqlite_db()`.
   - Checks Neo4j Desktop connectivity via `get_neo4j_client().verify_connectivity()`. If connected, executes `init_db_schema()`.
   - On shutdown: Closes the Neo4j driver connection safely (`client.close()`).
2. Registers all modular sub-routers:
   - `/documents` -> [`api/routes/documents.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/documents.py)
   - `/retrieval` -> [`api/routes/retrieval.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/retrieval.py)
   - `/qa`        -> [`api/routes/qa.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/qa.py)
   - `/graph`     -> [`api/routes/graph.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/graph.py)
3. Exposes the server via Uvicorn on `http://0.0.0.0:8000`.

---

## Step 5: Document Upload & Ingestion Engine (`api/routes/documents.py`, `utils/parsers.py`, `services/ingestion.py`)

This is where document processing begins when a user uploads a PDF.

### Files:
- [`api/routes/documents.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/documents.py)
- [`utils/parsers.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/utils/parsers.py)
- [`services/ingestion.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/ingestion.py)

### Detailed Ingestion Sequence:

```
[User Upload] -> POST /documents/upload
                      |
                      v
             1. Save to uploads/
             2. Log SQLite 'Processing'
             3. Launch Background Task: process_document()
                      |
                      v
             [services/ingestion.py]
                      |
        +-------------+-------------+
        |                           |
        v                           v
  parse_pdf()             RecursiveCharacterTextSplitter
  (PyMuPDF extract)       (chunk_size=1000, overlap=200)
        |                           |
        +-------------+-------------+
                      |
                      v
        1. save_to_neo4j() -> Document, Chunk, NEXT_CHUNK
        2. FAISS vector store -> Embed & Index Chunks
        3. process_chunks_async() -> LLM Graph Extraction
```

1. **API Endpoint (`api/routes/documents.py`)**:
   - `POST /documents/upload`: Saves the uploaded file to `uploads/`, logs ingestion start in SQLite, and dispatches `background_tasks.add_task(process_document, file_path)` so the endpoint returns immediately.
   - `GET /documents/history`: Returns SQLite ingestion logs.
   - `GET /documents/status/{filename}`: Polls processing status.
2. **PDF Parser (`utils/parsers.py`)**:
   - `parse_pdf(file_path)` uses PyMuPDF (`fitz`) to read text page-by-page, capturing text and original page numbers.
3. **Orchestrator (`services/ingestion.py`)**:
   - Creates a unique `DocumentModel`.
   - Uses `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` to break pages into text chunks.
   - `save_to_neo4j()`: Runs Cypher to create `(:Document)`, `(:Chunk)` nodes, connects them with `[:HAS_CHUNK]`, and links sequential chunks with `[:NEXT_CHUNK]`.
   - Sends chunks to `VectorStoreManager` to embed and store in FAISS.
   - Triggers `process_chunks_async(chunk_models)` for LLM graph extraction.

---

## Step 6: Dynamic Entity Extraction & Knowledge Graph Construction (`services/extraction.py`, `services/graph_builder.py`)

Extracting entities and relations from text requires LLM structured output and parameter-safe graph insertion.

### Files:
- [`services/extraction.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/extraction.py)
- [`services/graph_builder.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/graph_builder.py)

### Detailed Extraction & Graph Building Sequence:

#### 1. Structured LLM Extraction (`services/extraction.py`)
- `get_llm()` connects to OpenRouter via LangChain's `ChatOpenAI` wrapper pointing to `https://openrouter.ai/api/v1` with model `openai/gpt-4o-mini`.
- Uses `llm.with_structured_output(ExtractionResult)` to enforce strong typing matching `ExtractionResult(entities: List[EntityModel], relationships: List[RelationshipModel])`.
- Prompt instructs **Dynamic Ontology Extraction**:
  - Automatically infer entity categories (e.g., `Disease`, `Organization`) in `PascalCase`.
  - Automatically infer relationship types in `UPPER_SNAKE_CASE` (e.g., `HAS_RISK_FACTOR`).
  - Normalize entity IDs for deduplication (`"Open AI"` and `"openai"` both map to `"openai"`).
- `aextract_knowledge_from_chunk()` executes extraction asynchronously using `asyncio.Semaphore(10)` to bound concurrent API requests and prevent rate-limiting.

#### 2. Neo4j Graph Insertion (`services/graph_builder.py`)
- `merge_entities_and_relations(chunk_id, entities, relationships)`:
  - Upserts entity nodes into Neo4j:
    ```cypher
    UNWIND $entities AS ent
    MERGE (e:Entity {id: ent.id})
    SET e.name = ent.name, e.type = ent.type
    ```
  - Connects source text chunks to extracted entities:
    ```cypher
    MATCH (c:Chunk {chunk_id: $chunk_id})
    MATCH (e:Entity {id: ent.id})
    MERGE (c)-[:MENTIONS]->(e)
    ```
  - Sanitizes relationship type names using regular expressions (`re.sub(r'[^A-Z0-9_]', '', ...)`) to prevent Cypher injection.
  - Merges entity-to-entity relationships:
    ```cypher
    MATCH (source:Entity {id: $source_id})
    MATCH (target:Entity {id: $target_id})
    MERGE (source)-[:RELATION_TYPE]->(target)
    ```

---

## Step 7: Hybrid Vector Store (`services/vector_store.py`)

Vector search handles semantic text similarity matching.

### File:
- [`services/vector_store.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/vector_store.py)

### Highlights:
- Embeddings Model: `HuggingFaceEmbeddings(model_name="BAAI/bge-m3")`.
- Vector DB: **FAISS**.
- Index Persistence: Index files are saved locally in the `faiss_index/` directory.
- `_load_or_create_index()` automatically reloads an existing index on disk or creates a new one.
- `add_chunks()` converts chunk text and metadata into FAISS vectors and persists them.

---

## Step 8: Retrieval Engine & Cypher Query Generation (`services/retrieval.py`, `api/routes/retrieval.py`)

This is one of the most critical mechanisms in the system: converting user natural language questions into accurate Cypher queries for Neo4j while combining them with vector search.

### Files:
- [`services/retrieval.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/retrieval.py)
- [`api/routes/retrieval.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/retrieval.py)

### How Cypher Query Generation Works (Deep Dive):

```
 User Question: "What risk factors are associated with Obesity?"
                         |
                         v
       [services/retrieval.py: graph_search()]
                         |
  1. Fetch DB Relationship Types: session.run("CALL db.relationshipTypes()")
  2. Dynamically Inject Schema into GraphCypherQAChain
  3. Format Custom CYPHER_GENERATION_PROMPT
                         |
                         v
                OpenRouter LLM Call
                         |
                         v
 Generated Cypher:
 MATCH (a:Entity {type: 'Disease'})-[r:HAS_RISK_FACTOR]->(b:Entity)
 WHERE toLower(a.name) CONTAINS toLower('Obesity')
 RETURN a, r, b
                         |
                         v
       Execute Query on Neo4j -> Return Multi-Hop Graph Paths
```

1. **Bypassing APOC Dependency**:
   - Standard LangChain `Neo4jGraph` attempts to call APOC procedures for schema inspection, which fails if APOC isn't installed in Neo4j Desktop.
   - `graph_search()` manually queries `CALL db.relationshipTypes()` via Neo4j session and constructs a clean schema string dynamically:
     ```python
     graph.schema = (
         "Node properties are the following:\n"
         "Entity {name: STRING, type: STRING}\n"
         "The relationships are the following:\n"
         f"{', '.join(rel_paths)}\n"
     )
     ```
2. **Strict Rules in `CYPHER_GENERATION_PROMPT`**:
   - Always use the `:Entity` label (never invent labels like `:Disease`).
   - Filter categories using `e.type` property.
   - Use `toLower()` for case-insensitive matching (`WHERE toLower(a.name) CONTAINS toLower(...)`).
   - Enforce document-level scoping when requested by matching `(d:Document {filename: $filename})-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)`.
3. **Execution & Context Assembly**:
   - `GraphCypherQAChain` generates the Cypher string and executes it against Neo4j.
   - `hybrid_search()` runs both `vector_search()` and `graph_search()`.
   - `assemble_context()` combines textual document excerpts and graph relation paths into a single structured prompt for answer generation.

---

## Step 9: Answer Generation & Q&A (`services/generation.py`, `api/routes/qa.py`)

Generates accurate natural language responses grounded exclusively in retrieved context.

### Files:
- [`services/generation.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/generation.py)
- [`api/routes/qa.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/qa.py)

### Sequence:
1. API receives POST request on `/qa/ask` with JSON body: `{"query": "...", "top_k": 5, "filename": "doc.pdf"}`.
2. Invokes `hybrid_search()` and `assemble_context()`.
3. Calls `generate_answer(query, context)`:
   - System prompt instructs the LLM to use **ONLY** the provided semantic and relational context.
   - Forbids outside knowledge or hallucination.
   - If facts are missing, returns `"I don't have enough information to answer that based on the provided documents."`
4. Response returns:
   - Generated answer text.
   - Context used.
   - Generated Cypher query string.
   - Document source citations.

---

## Step 10: Graph Visualization API (`api/routes/graph.py`)

Translates internal graph structures into interactive visualization payloads.

### File:
- [`api/routes/graph.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/graph.py)

### Details:
- Endpoint: `GET /graph/visualize/{filename}`.
- Cypher query matches document chunks, mentioned entities, and inter-entity relationships:
  ```cypher
  MATCH (d:Document {filename: $filename})-[:HAS_CHUNK]->(c:Chunk)
  OPTIONAL MATCH (c)-[:MENTIONS]->(e1:Entity)
  OPTIONAL MATCH (c)-[:MENTIONS]->(e2:Entity)
  OPTIONAL MATCH (e1)-[r]->(e2)
  RETURN d, c, e1, r, e2
  ```
- Formats records into `nodes` (with groups: `Document`, `Chunk`, `Entity` categories) and `edges` (labels: `HAS_CHUNK`, `MENTIONS`, dynamic relationship types).

---

## Step 11: Streamlit User Interface (`ui.py`)

The Streamlit dashboard provides a interactive visual interface for the system.

### File:
- [`ui.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/ui.py)

### Three Main Pages:
1. **Ingestion**:
   - Drag-and-drop PDF uploader.
   - Progress bar with real-time polling to `/documents/status/{filename}`.
   - Ingestion history feed connected to `/documents/history`.
2. **Knowledge Graph**:
   - Renders visual graph using `streamlit-agraph`.
   - Node selection panel showing entity properties, entity type, and incoming/outgoing edges.
3. **Chat / Q&A**:
   - Interactive chat window.
   - Displays assistant answer along with formatted **Inference Path (Cypher/SQL)** code blocks and source file badges.

---

## Sequence Summary & Cheat Sheet

To follow a request through the codebase step-by-step, use this cheat sheet:

| Phase | Entry File / Function | Key Operations | Next Step |
|---|---|---|---|
| **Config Initialization** | [`core/config.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/core/config.py) | Loads `.env` variables | [`db/neo4j_client.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/db/neo4j_client.py) |
| **Server Startup** | [`main.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/main.py#L8-L26) | Verifies Neo4j & initializes schema in [`db/cypher_init.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/db/cypher_init.py) | Ready for API requests |
| **Document Upload** | [`api/routes/documents.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/documents.py#L16-L35) | Saves PDF to `uploads/`, logs to SQLite | Background task `process_document()` |
| **Parsing & Chunking** | [`services/ingestion.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/ingestion.py#L79-L134) | PyMuPDF parsing via [`utils/parsers.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/utils/parsers.py) & text splitting | Neo4j Chunk save + FAISS embedding |
| **Entity Extraction** | [`services/extraction.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/extraction.py#L60-L93) | OpenRouter LLM structured extraction | [`services/graph_builder.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/graph_builder.py) |
| **Graph Upsert** | [`services/graph_builder.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/graph_builder.py#L6-L46) | Merges `Entity` nodes & dynamic Cypher relations | Graph ready in Neo4j |
| **User Question** | [`api/routes/qa.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/api/routes/qa.py#L16-L30) | Receives query from [`ui.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/ui.py) | Calls `hybrid_search()` |
| **Cypher Generation** | [`services/retrieval.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/retrieval.py#L35-L135) | Translates query to Cypher via `GraphCypherQAChain` | Combines FAISS + Cypher paths |
| **LLM Synthesis** | [`services/generation.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/services/generation.py#L5-L40) | Formats grounding context & calls LLM | Returns answer + Cypher to [`ui.py`](file:///d:/Fxis.ai/Rag's/Graph-QA/ui.py) |
