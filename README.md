# Knowledge-Graph-QA

Comprehensive, enterprise-grade hybrid Knowledge Graph Q&A engine combining semantic vector search (RAG) with a structured knowledge graph (GraphRAG). This repository implements a production-ready pipeline for ingesting documents (PDFs), extracting entities and relations with LLM assistance, storing facts in Neo4j, indexing textual chunks with FAISS, and answering natural language questions using a hybrid retrieval strategy.

This README provides a detailed technical overview, architecture, deployment and development instructions, API reference and troubleshooting guidance to help maintainers and contributors understand, run, and extend the project.

---

Table of Contents
1. Project Overview
2. Key Features
3. Architecture & Data Flow
4. Data Model & Ontology Concepts
5. Technology Stack
6. Project Layout
7. Quickstart — Local Development
8. Configuration & Environment Variables
9. Running & Using the System
10. API & UI Endpoints
11. Ingestion Pipeline (Detailed)
12. Retrieval & Answering Flow
13. Examples
14. Testing & CI
15. Deployment & Scaling Notes
16. Troubleshooting & FAQ
17. Contributing
18. License & Acknowledgements

---

1. Project Overview

Knowledge-Graph-QA is designed to remove the weaknesses of pure Vector-RAG by combining:

- High‑recall semantic search over text chunks (FAISS embeddings).
- Precise, explainable multi‑hop reasoning over a canonical knowledge graph (Neo4j).
- LLM-driven extraction and answer synthesis with full source provenance and inference path reporting.

The result: accurate factual answers, multi-hop reasoning capability, and auditability for enterprise use.


2. Key Features

- Document ingestion (PDF) with chunking and metadata preservation.
- LLM-powered entity and relation extraction with dynamic ontology discovery.
- FAISS-based vector store for efficient semantic retrieval.
- Neo4j knowledge graph with node/relationship merging and provenance tracking.
- Hybrid search combining vector and graph retrieval for robust answers.
- Explainability: returned Cypher inference path and source badges for every answer.
- Streamlit UI for ingestion, graph visualization and chat-style Q&A.
- Lightweight SQLite audit log for ingestion history and metadata.


3. Architecture & Data Flow

High-level pipeline (ASCII):

                       +---------------------+
                       |  User / Dashboard   |
                       +---------+-----------+
                                 |
                            HTTP | WebSocket
                                 |
                       +---------v-----------+
                       |    FastAPI Backend  |
                       +----+---------+------+
                            |         |
            +---------------+         +----------------+
            |                                        |
    +-------v------+                         +-------v------+
    |   FAISS Vec   |                         |   Neo4j KG   |
    |   (Chunks)    |                         | (Nodes/Edges) |
    +---------------+                         +---------------+
            ^                                          ^
            |                                          |
            +------------+     +-----------------------+
                         |     |
                  +------v-----v-------+
                  |    Ingestion LLM    |
                  | (Entity & Triple    |
                  |   extraction)       |
                  +---------------------+

Steps:
1. Upload PDF → chunk → embed → store in FAISS with chunk metadata.
2. Send chunk to LLM extractor → produce entities/triples and metadata.
3. Merge triples into Neo4j using parameterized Cypher (MERGE for canonicalization).
4. On query: run FAISS vector search to get relevant chunks and run graph Cypher queries for multi-hop evidence. Merge results and synthesize final LLM answer with sources and inference path.


4. Data Model & Ontology Concepts

This project follows common semantic-web/description-logics conventions. Two main layers are modeled:

- TBox (Terminology Box): ontology/schema — labels, relationship types, domain/range constraints.
- ABox (Assertion Box): instance-level facts and document-level evidence.

Important entities in the graph:

- Document: root node for provenance (filename, upload time, pages).
- Chunk: a contiguous piece of document text (text, offset, page, chunk_id).
- Entity: canonical named entity (name, type(s), summary, canonical_id).
- Relation: labeled edge between Entities (property like TREATED_BY, HAS_SYMPTOM).

Best practices implemented:
- Every assertion contains provenance linking back to the originating Chunk and Document.
- Entities extracted across multiple chunks/documents are MERGEd to one canonical node using unique keys (e.g., normalized name + type).


5. Technology Stack

- Python 3.10+
- FastAPI (backend HTTP API)
- Streamlit (frontend dashboard/UI)
- Neo4j (graph database)
- FAISS (vector index)
- LangChain + langchain-neo4j integration
- LLM connector(s): OpenRouter / provider of choice
- Embeddings: BAAI/bge-m3 (or pluggable alternative)
- SQLite (ingestion audit store)
- Uvicorn (ASGI server)


6. Project Layout

(Top-level structure — updated to match codebase)

Graph-QA/
├── api/                    # FastAPI route modules (documents, graph, qa, retrieval)
├── core/                   # Configuration and app-wide utilities
├── db/                     # Neo4j and SQLite clients, schema initialization
├── models/                 # Pydantic models and schemas
├── services/               # Business logic: ingestion, extraction, graph-builder, retrieval
├── .streamlit/             # Streamlit UI config
├── app.db                  # SQLite ingestion audit DB (generated)
├── main.py                 # FastAPI application entry point
├── ui.py                   # Streamlit dashboard integration
└── requirements.txt        # Python dependencies


7. Quickstart — Local Development

Prerequisites
- Python 3.10+
- Neo4j (Desktop or Community Server) accessible via bolt://localhost:7687
- Git

Clone and install

```bash
git clone https://github.com/saket0x07/Knowledge-Graph-QA.git
cd Knowledge-Graph-QA
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows (PowerShell)
# .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Set up Neo4j
- Start Neo4j and ensure credentials are set. Note the bolt URI and username/password.

Create .env file

Create a `.env` in the repository root with the following (example):

```env
OPENROUTER_API_KEY=your_openrouter_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
# Optional / advanced
EMBEDDINGS_MODEL=BAAI/bge-m3
VECTOR_STORE_PATH=./data/faiss_index
SQLITE_PATH=./app.db
```

Run services locally

1. Start FastAPI backend:

```bash
python -m uvicorn main:app --reload
```

2. Start Streamlit UI in a second terminal:

```bash
streamlit run ui.py
```

Open the Streamlit UI at http://localhost:8501 and interact with ingestion, graph visualizer and Q&A.


8. Configuration & Environment Variables

- OPENROUTER_API_KEY — API key for LLM provider (required to call LLMs).
- NEO4J_URI — bolt URI for Neo4j (default bolt://localhost:7687).
- NEO4J_USER, NEO4J_PASSWORD — Neo4j authentication credentials.
- EMBEDDINGS_MODEL — name/id of the embeddings model (default BAAI/bge-m3).
- VECTOR_STORE_PATH — path to persist FAISS vector index.
- SQLITE_PATH — path to SQLite DB for ingestion audits.

Secrets should be stored in `.env` or injected into the environment via your chosen secret management.


9. Running & Using the System

Typical workflow:
1. Upload a PDF via the Streamlit UI or POST to the /documents endpoint.
2. The ingestion pipeline chunks the PDF, stores text embeddings in FAISS, and runs the extractor LLM to populate Neo4j.
3. Query the system from the GraphMind UI (chat) or call the /qa endpoint with a question and an optional `filename` scope.
4. The system returns an answer with: text response, list of source chunks/documents, and the Cypher inference path used.


10. API & UI Endpoints

(Assumes routes implemented under api/ directory; adjust if file names differ)

- POST /documents/upload — upload PDF and trigger asynchronous ingestion
- GET /documents/history — list ingestion history (from SQLite)
- GET /graph/visualize?filename=<file> — returns graph payload for visualization
- POST /qa — main hybrid QA endpoint; body: { question: string, filename?: string }
- POST /retrieval — direct retrieval endpoint returning top N FAISS chunks

Example cURL (QA)

```bash
curl -X POST http://localhost:8000/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "What treatments are recommended for diabetes?", "filename": "diabetes_paper.pdf"}'
```

Response (example)
```
{
  "answer": "...",
  "sources": ["diabetes_paper.pdf:chunk-12", "diabetes_review.pdf:chunk-3"],
  "inference_path": "MATCH (d:Document {filename: '...'})-[:HAS_CHUNK]->(c)-[:MENTIONS]->(e) ..."
}
```


11. Ingestion Pipeline (Detailed)

1. PDF Loading & Chunking
   - PyPDFLoader extracts text by page.
   - RecursiveCharacterTextSplitter (chunk_size=1000, chunk_overlap=200) produces chunks with metadata (page, offset).

2. Embeddings & Vector Storage
   - Each chunk is embedded using the configured embeddings model and upserted into FAISS along with metadata (document filename, chunk_id, page).

3. LLM Extraction to Graph
   - Each chunk is sent to an LLM extraction chain which returns:
     - Entities with type(s) and normalized name
     - Triples (subject, predicate, object) with confidence and evidence pointers (offsets)
   - Graph builder creates parameterized Cypher MERGE queries to insert/merge nodes and relationships while attaching provenance (Chunk, Document).

4. Audit Log
   - The ingestion event and metadata are written to SQLite (`app.db`) for auditing and to power the ingestion history UI.

Important notes
- The extraction LLM should be run with temperature=0 (deterministic) for canonical triples when possible.
- Deduplication and merge rules live in the graph_builder service.


12. Retrieval & Answering Flow

On a user query the system performs the following steps:

A. Vector Retrieval
- Use FAISS to get top-K chunks by cosine similarity. Optionally filter by filename for local search.

B. Graph Cypher Search
- Use a GraphCypherQAChain which inspects the graph and constructs Cypher queries to find multi-hop evidence.
- In local mode, constrain Cypher queries to chunks linked to the selected document.

C. Context Assembly
- Combine unique graph results and vector chunks into a deduplicated context fed to the final LLM for answer generation.

D. Answer Generation
- LLM synthesizes a concise answer and returns the inference path (Cypher) and sources for auditability.


13. Examples

Example: Local scoped question (Streamlit UI)
- Select document "diabetes_paper.pdf" → Ask: "Which treatments reduce A1C for type 2 diabetes?"
- The system returns: summarized treatments, citations to document chunk IDs, and a Cypher inference path showing relationships between treatments and outcome measures.


14. Testing & CI

- Unit tests: add tests under tests/ for services (ingestion, vector_store, graph_builder).
- Integration tests: create test fixtures that spin up a test Neo4j instance (or use Neo4j test harness) and a temporary FAISS index.
- CI: ensure environment variables are injected in the pipeline and secrets are masked.


15. Deployment & Scaling Notes

- Neo4j: for production consider Neo4j Aura or clustered Neo4j Enterprise for scale and HA.
- Vector Index: FAISS is file-backed and suitable for single-machine usage. For distributed/managed solutions consider Milvus, Pinecone, or OpenSearch k-NN.
- LLMs: use provider quotas and batching. Use async processing and rate-limiting for ingestion and querying.
- Storage: persist FAISS index periodically and back up Neo4j regularly.


16. Troubleshooting & FAQ

Q: Neo4j connection fails (Authentication error)
A: Confirm NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD in `.env`. Start Neo4j Desktop or service and verify bolt port.

Q: Streamlit UI does not load
A: Ensure `streamlit run ui.py` is running and check console logs for missing dependencies. Confirm backend is up (main:app).

Q: Embeddings or LLM calls fail
A: Verify OPENROUTER_API_KEY is present and valid. Check provider status and rate limits.


17. Contributing

Thank you for your interest in contributing! Typical contribution areas:
- Bug fixes and improvements to the ingestion/extraction pipeline.
- New extractor prompt templates, type resolvers or merge strategies.
- UI enhancements and graph visualization features.
- Tests and CI improvements.

Guidelines:
- Fork the repo, create a feature branch, open a PR with a descriptive title and detailed description of changes.
- Write tests for new features and ensure existing tests pass.
- Follow repo code style (black/flake8 if configured).


18. License & Acknowledgements

- Replace or add a LICENSE file in the repository root as appropriate for your project (MIT, Apache-2.0, etc.).
- Acknowledge 3rd-party libraries and projects used (LangChain, Neo4j, FAISS, Streamlit).

---

If you'd like, I can also:
- Add a short example notebook that demonstrates ingestion and a sample Q&A flow.
- Create a Docker Compose file to spin up Neo4j, the FastAPI backend and a worker for ingestion.
- Add unit/integration test templates and CI config for GitHub Actions.

If that sounds good, I will commit the changes now.