# 🕸️ Knowledge-Graph-QA — Hybrid GraphRAG & Knowledge Graph Q&A

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production-ready-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

A production‑oriented, hybrid Knowledge Graph Q&A engine combining semantic vector search (RAG) with a canonical knowledge graph (GraphRAG). Designed for accurate multi‑hop reasoning, verifiable inference paths, and enterprise ingestion workflows.

Quick link: Demo UI → streamlit at http://localhost:8501 (when running locally)

---

✨ Why this project

- Vector-only RAGs are powerful but can hallucinate relationships and struggle with multi‑hop reasoning. Knowledge-Graph-QA combines high‑recall semantic retrieval (FAISS) with an explainable Neo4j knowledge graph and LLM-assisted extraction to provide accurate, auditable answers.

---

## 🚀 Highlights

- 🔎 Hybrid retrieval: FAISS vector search + Neo4j Cypher-based reasoning
- 🧩 LLM-powered dynamic ontology extraction (TBox discovery + ABox assertions)
- 📚 Full provenance: Document → Chunk → Entity linking for traceability
- 🎛 Streamlit UI for ingestion, graph visualization and chat-style Q&A
- 🧪 Lightweight audit trail with SQLite for ingestion history

---

## 📦 At a glance (TL;DR)

1. Upload PDFs via UI or API
2. Pipeline chunks text, generates embeddings (BAAI/bge-m3), stores in FAISS
3. LLM extracts entities/triples from chunks and MERGEs them into Neo4j
4. Ask a question → system runs vector + graph retrieval → LLM synthesizes answer with inference path and sources

---

## 🧭 Project style & structure (Agentic README inspired)

This README uses clear sections, emoji-labelled feature bullets, and short operational examples so you can get started fast.

## 🔧 Technology Stack

- Python 3.10+
- FastAPI + Uvicorn
- Neo4j (bolt)
- FAISS (local vector store)
- LangChain, langchain-neo4j
- Streamlit (UI)
- SQLite (ingestion audit)
- LLMs via OpenRouter (configurable)

---

## 📁 Repository layout (short)

Graph-QA/
- api/ — FastAPI routes (documents, graph, qa, retrieval)
- core/ — config & settings
- db/ — neo4j and sqlite clients, cypher init
- models/ — Pydantic schemas
- services/ — ingestion, extraction, graph builder, retrieval, vector store
- ui.py — Streamlit dashboard
- main.py — FastAPI entrypoint
- requirements.txt

---

## ✨ Quick Start — Local (5 minutes)

Prerequisites: Python 3.10+, Neo4j running (bolt://localhost:7687).

1) Clone & install

```bash
git clone https://github.com/saket0x07/Knowledge-Graph-QA.git
cd Knowledge-Graph-QA
python -m venv venv
source venv/bin/activate   # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2) Create `.env` (example)

```env
OPENROUTER_API_KEY=your_openrouter_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
EMBEDDINGS_MODEL=BAAI/bge-m3
VECTOR_STORE_PATH=./data/faiss_index
SQLITE_PATH=./app.db
```

3) Start backend and UI

```bash
# Terminal 1
python -m uvicorn main:app --reload

# Terminal 2
streamlit run ui.py
```

Open http://localhost:8501 and start ingesting PDFs.

---

## 🛠 How it works (concise)

1. Ingestion
   - PyPDFLoader → RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
   - Embed chunks → FAISS (persist metadata: filename, page, chunk_id)
   - LLM extracts entities & triples → graph_builder MERGEs into Neo4j with provenance links

2. Query
   - FAISS returns top-K chunks (optionally filtered by filename)
   - GraphCypherQAChain inspects Neo4j to create multi-hop evidence queries
   - Assembly: dedupe vector passages + graph results
   - Final LLM answer produced with: answer text, sources (chunk IDs), and inference_path (Cypher)

---

## 🔎 Example: Ask via API

Request

```bash
curl -X POST http://localhost:8000/qa \
  -H "Content-Type: application/json" \
  -d '{"question": "What treatments reduce A1C for type 2 diabetes?", "filename": "diabetes_paper.pdf"}'
```

Response (example)

```json
{
  "answer": "Metformin and GLP-1 receptor agonists have shown consistent A1C reductions...",
  "sources": ["diabetes_paper.pdf:chunk-12", "review_diabetes.pdf:chunk-3"],
  "inference_path": "MATCH path = (t:Treatment)-[:TREATED_FOR]->(d:Disease {name:'Type 2 diabetes'}) ..."
}
```

---

## 🧾 Best practices & notes

- Extraction LLM: use temperature=0 for deterministic triples
- Merge keys: normalize entity names and prefer canonical identifiers when available
- Keep chunk overlap sufficient to preserve context across sentence boundaries
- For production: consider managed vector stores (Pinecone/Milvus) and Neo4j Enterprise/Aura

---

## 🛡 Security & Guardrails

- Read-only by default for most agent operations; only ingestion and graph updates require write permissions.
- Keep API keys and credentials out of source control — use `.env` or secret manager.
- Rate-limit LLM calls and batch ingestion to avoid provider quota exhaustion.

---

## 🧪 Testing and CI

- Unit test candidates: services/vector_store.py, services/graph_builder.py, services/ingestion.py
- Integration tests should spin up a test Neo4j instance (or use Neo4j test harness) and a temporary FAISS index.
- Suggested GitHub Actions: linters (black/flake8), test matrix (python 3.10+), and integration job using service containers.

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Add tests for new behavior
4. Open a PR with a clear description and rationale

Be sure to follow code style (black) and include unit tests for core logic.

---

## 📜 License & Acknowledgements

This repository uses the MIT license — add a LICENSE file if not present.

Credits: LangChain, Neo4j, FAISS, Streamlit, OpenRouter and the open-source community for libraries and design patterns used here.

---

If you want, I can now:
- Add a polished README header with custom shields (CI, coverage)
- Create a `docker-compose.yml` to run Neo4j + backend + optional worker
- Convert the README into a shorter GitHub Home page and a deeper `docs/` folder

Tell me which one to do next.