# 🕸️ Hybrid GraphRAG & Knowledge Graph Q&A Engine

Welcome to the **Hybrid Knowledge Graph QA** project—an end-to-end, enterprise-grade **GraphRAG (Graph Retrieval-Augmented Generation)** platform. This system combines **Semantic Vector Search (FAISS)** with **Structured Relational Reasoning (Neo4j Graph Database)**, wrapped in a modern **FastAPI** backend and an intuitive **Streamlit** dashboard.

This README is designed to serve as both a **System Architecture Guide** and a **Comprehensive Revision Manual** covering advanced Knowledge Graph concepts, ontology ingestion paradigms, chunking strategies (TBox vs. ABox), and hybrid search dynamics.

---

## 📚 Table of Contents
1. [Theoretical Foundations & Core Concepts](#-theoretical-foundations--core-concepts)
   - [Why Traditional Vector RAG Fails](#why-traditional-vector-rag-fails)
   - [TBox vs. ABox in Knowledge Graphs](#tbox-vs-abox-in-knowledge-graphs)
   - [The Orphan Axiom Problem](#the-orphan-axiom-problem)
   - [The 3 Ingestion Techniques for GraphRAG](#the-3-ingestion-techniques-for-graphrag)
   - [Dynamic Ontology Extraction](#dynamic-ontology-extraction)
2. [System Architecture & Data Pipeline](#-system-architecture--data-pipeline)
   - [Ingestion Workflow](#1-ingestion-workflow)
   - [Hybrid Retrieval & Local vs. Global Search](#2-hybrid-retrieval--local-vs-global-search)
   - [Generation & Explainability](#3-generation--explainability)
3. [Technology Stack](#-technology-stack)
4. [Project Structure](#-project-structure)
5. [User Interface & Dashboard Overview](#-user-interface--dashboard-overview)
6. [Quickstart & Installation](#-quickstart--installation)
7. [Cypher & Neo4j Cheat Sheet for Revision](#-cypher--neo4j-cheat-sheet-for-revision)

---

## 🧠 Theoretical Foundations & Core Concepts

### Why Traditional Vector RAG Fails
Standard Vector RAG embeds text passages into high-dimensional vector spaces and performs cosine similarity matching. While excellent for localized semantic similarity, it suffers from critical limitations:
* **Loss of Global Context:** Vector search cannot easily summarize overarching themes across an entire corpus.
* **Multi-Hop Reasoning Blindspot:** It cannot connect disparate entities across separate documents (e.g., *Document A: "Company X acquired Company Y"* and *Document B: "Company Y manufactures Component Z"* -> *Query: "What components does Company X now control?"*).
* **Hallucination of Relationships:** Vector distances reflect semantic proximity, not factual assertion.

**GraphRAG** addresses these flaws by organizing facts into explicit nodes and labeled edges, allowing exact multi-hop traversals and global reasoning.

---

### TBox vs. ABox in Knowledge Graphs
When modeling domain knowledge in Description Logics and Knowledge Graphs, knowledge is partitioned into two distinct components:

| Component | Full Name | Definition | Example in our Project |
| :--- | :--- | :--- | :--- |
| **TBox** | *Terminology Box* | The **schema or ontology**. Defines the structural rules, entity classes, properties, and relationship types. | Entity Types: `[:Disease]`, `[:Treatment]`, `[:Symptom]`. Relationships: `[:TREATED_BY]`, `[:HAS_SYMPTOM]`. |
| **ABox** | *Assertion Box* | The **instance data or facts**. Populates the TBox schema with concrete entities, document chunks, and real-world instances. | `(Diabetes:Entity {type: 'Disease'}) -[:TREATED_BY]-> (Insulin:Entity {type: 'Treatment'})` |

---

### The Orphan Axiom Problem
In traditional ontology-driven RAG systems, text chunking often creates **Orphan Axioms**—instance assertions (ABox facts) that become disconnected from their structural class hierarchy (TBox rules) or parent document context during splitting.

#### How Our Hybrid Architecture Solves It:
1. **Document & Chunk Anchoring:** Every extracted entity and relationship is connected back to a parent `Chunk` node, which in turn links to a `Document` node in Neo4j (`(Document)-[:HAS_CHUNK]->(Chunk)-[:MENTIONS]->(Entity)`).
2. **Context-Enriched Chunking:** We combine semantic character splitting with vector embeddings containing full document metadata (`source`, `page_number`), ensuring no assertion is left without context.

---

### The 3 Ingestion Techniques for GraphRAG
Modern Knowledge Graph ingestion generally follows one of three paradigms:

1. **Entity Reader (Relational Thinking):** Extracts tabular/structured data into strict relational schemas. Highly precise, but rigid.
2. **Graph Reader (NoSQL Thinking):** Extract raw triples `(Subject, Predicate, Object)` directly from unstructured text without predefined schemas. Extremely flexible, but can lead to entity duplication and sparse graphs.
3. **Hybrid + Ontology (Graph Thinking) — *Implemented in this Project*:**
   - **Step 1:** Extract structured entities and metadata from text chunks using an LLM.
   - **Step 2:** Discover dynamic ontologies (relational facts and atomic assertions) on the fly.
   - **Step 3:** Merge identical entities into a unified graph network while maintaining source provenance.

---

### Dynamic Ontology Extraction
Rather than requiring developers to write complex, static schema definitions beforehand, our ingestion pipeline uses LLM-powered dynamic extraction:
* As a PDF is processed, the LLM reads chunks and dynamically identifies entity categories (`Disease`, `Treatment`, `Symptom`, `Concept`, etc.) and relationship types (`HAS_SYMPTOM`, `TREATED_BY`, `COMORBID_WITH`).
* Identical entities extracted across different pages or documents are automatically merged into single nodes in Neo4j using `MERGE (e:Entity {name: ...})`.

---

## 🏗️ System Architecture & Data Pipeline

```
                       ┌───────────────────────────────┐
                       │       PDF Document Upload     │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │  Recursive Character Splitter │
                       │    (Chunk Size: 1000, 200)    │
                       └───────────────┬───────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │  FAISS Vector Index   │             │   LLM Entity & Triple │
        │ (BAAI/bge-m3 Embeds)  │             │       Extraction      │
        └───────────┬───────────┘             └───────────┬───────────┘
                    │                                     │
                    │                                     ▼
                    │                         ┌───────────────────────┐
                    │                         │     Neo4j Database    │
                    │                         │ (Nodes & Relationships│
                    │                         └───────────┬───────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │     Hybrid Search Engine      │
                       │  (Vector Filter + Cypher QA)  │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    LLM Answer Generation      │
                       │  + Inference Path Display     │
                       └───────────────┬───────────────┘
```

### 1. Ingestion Workflow
1. **Document Loading:** PyPDFLoader reads the PDF and extracts raw text page-by-page.
2. **Text Chunking:** `RecursiveCharacterTextSplitter` divides text into manageable chunks (`chunk_size=1000`, `chunk_overlap=200`).
3. **Vector Storage:** Chunks are embedded using `BAAI/bge-m3` via `langchain_huggingface` and stored in a local FAISS vector store with source metadata.
4. **Graph Store Load:** Each chunk is processed by the LLM (`OpenRouter / DeepSeek / GPT-4`) to extract nodes and edge triples, which are written into Neo4j using parameterized Cypher queries.
5. **Audit Logging:** Ingestion metadata (file name, size, status, timestamp) is recorded in an **SQLite** database (`app.db`).

---

### 2. Hybrid Retrieval & Local vs. Global Search
When a user asks a question, our backend triggers `hybrid_search`:

#### A. Semantic Vector Search
* Executes a cosine-similarity search against FAISS.
* **Local Search Mode:** Applies a metadata filter `{"source": filename}` to restrict search to a specific PDF.
* **Global Search Mode:** Searches across all vector chunks in the index.

#### B. Knowledge Graph Search
* Uses `GraphCypherQAChain` to inspect the Neo4j schema dynamically and synthesize a Cypher statement.
* **Local Search Mode:** Injects a prompt rule forcing Cypher queries to match entities connected to the specified `filename` (`MATCH (d:Document {filename: ...})-[:HAS_CHUNK]->(c)-[:MENTIONS]->(e:Entity)...`).
* **Global Search Mode:** Queries the entire graph network without document boundary constraints.

---

### 3. Generation & Explainability
* **Context Assembly:** Vector passages and Cypher path strings are merged into a single deduplicated prompt context.
* **Final Generation:** The LLM synthesizes a concise response strictly using the provided context.
* **Explainability UI:** The frontend displays the generated **Inference Path (Cypher query)** and **Sources Found (Document badges)** for complete auditability.

---

## 🛠️ Technology Stack

* **Backend API:** FastAPI, Uvicorn, Pydantic
* **Frontend Dashboard:** Streamlit, Streamlit-Agraph (HTML5 Canvas physics visualization)
* **Graph Database:** Neo4j (Community Edition / Desktop)
* **Vector Database:** FAISS (Facebook AI Similarity Search)
* **Relational Database:** SQLite (Ingestion Audit Trail)
* **LLM Orchestration:** LangChain, `langchain-neo4j`, `langchain-huggingface`
* **Embeddings Model:** `BAAI/bge-m3`
* **LLM Provider:** OpenRouter API

---

## 📁 Project Structure

```
Graph-QA/
├── api/
│   └── routes/
│       ├── documents.py     # Upload & Ingestion history endpoints
│       ├── graph.py         # Graph visualization payload endpoint
│       ├── qa.py            # Hybrid Q&A endpoint
│       └── retrieval.py     # Direct retrieval endpoint
├── core/
│   └── config.py            # App settings & environment variables
├── db/
│   ├── cypher_init.py       # Neo4j schema, indexes, & constraints
│   ├── neo4j_client.py      # Neo4j driver connection manager
│   └── sqlite_client.py     # SQLite history database manager
├── models/
│   └── schema.py            # Pydantic data models for extraction
├── services/
│   ├── extraction.py        # LLM initialization
│   ├── generation.py        # Final answer synthesis service
│   ├── graph_builder.py     # Cypher MERGE query builder
│   ├── ingestion.py         # Async document processing pipeline
│   ├── retrieval.py         # Hybrid search engine (FAISS + Cypher)
│   └── vector_store.py      # FAISS vector store manager
├── .streamlit/
│   └── config.toml          # Streamlit visual theme configuration
├── app.db                   # SQLite ingestion history database
├── main.py                  # FastAPI application entrypoint
├── ui.py                    # Streamlit 3-section dashboard UI
└── requirements.txt         # Project Python dependencies
```

---

## 🎨 User Interface & Dashboard Overview

The Streamlit UI (`ui.py`) features a sleek, multi-view sidebar navigation:

1. **Data Ingestion Engine:**
   - Drag-and-drop PDF uploader with real-time processing status polling.
   - Right-hand **Ingestion History** panel backed by SQLite.
2. **Knowledge Graph Visualizer:**
   - Full-canvas interactive node graph built with physics-based layout engine (`streamlit-agraph`).
   - Side panel showing **Node Details**, entity category badges, and **Connected Entities** (incoming/outgoing relationships).
3. **GraphMind Explorer (Chat / Q&A):**
   - **Persistent Knowledge Base Selector:** Switch between **Global (All Documents)** and specific PDFs in the sidebar.
   - **Recent Queries & Saved Insights** sidebar panel.
   - **Explainable Assistant Bubbles:** Displays response text, an **Inference Path (Cypher/SQL)** code box, and **Sources Found** pill tags.

---

## ⚡ Quickstart & Installation

### 1. Prerequisites
* Python 3.10+
* Neo4j Desktop or Neo4j Community Server running locally on `bolt://localhost:7687`

### 2. Environment Setup
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/saket0x07/Knowledge-Graph-QA.git
cd Knowledge-Graph-QA

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_api_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 4. Running the Application

Start the **FastAPI Backend**:
```bash
python -m uvicorn main:app --reload
```

In a second terminal, start the **Streamlit Dashboard**:
```bash
streamlit run ui.py
```

Open your browser to `http://localhost:8501`.

---

## 📝 Cypher & Neo4j Cheat Sheet for Revision

Use these Cypher snippets to inspect and debug your Knowledge Graph in Neo4j Browser:

### 1. View Schema Constraints & Indexes
```cypher
SHOW CONSTRAINTS;
```

### 2. Count Total Nodes by Label
```cypher
MATCH (n) 
RETURN labels(n) AS Label, count(*) AS Count;
```

### 3. Fetch All Entities and Relationships for a Specific Document
```cypher
MATCH (d:Document {filename: "ai_rag_notes.pdf"})-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e1:Entity)-[r]->(e2:Entity)
RETURN d, c, e1, r, e2 
LIMIT 50;
```

### 4. Find Multi-Hop Paths Between Two Entities
```cypher
MATCH path = shortestPath((e1:Entity {name: "Diabetes"})-[*..3]-(e2:Entity {name: "Hypertension"}))
RETURN path;
```

### 5. Wipe Graph Database (For Testing Reset)
```cypher
MATCH (n) DETACH DELETE n;
```

---

*Built with ❤️ for Advanced Knowledge Graph RAG Architectures.*
