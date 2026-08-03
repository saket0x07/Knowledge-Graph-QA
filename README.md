# Knowledge Graph QA (Hybrid RAG)

This project implements a robust Hybrid Retrieval-Augmented Generation (RAG) system by combining **Semantic Vector Search** (using FAISS) and **Knowledge Graph Retrieval** (using Neo4j). It is designed to dynamically extract ontologies from unstructured text and query them using an LLM-powered Cypher generator.

## Features

- **Dynamic Ontology Extraction:** Uses an LLM to dynamically discover and infer relevant Entity Types and Relationship Types based on context, without relying on a static, predefined schema.
- **Hybrid Retrieval:**
  - **Vector Search:** Uses `langchain_huggingface` embeddings stored in a local FAISS index to find semantically relevant text chunks.
  - **Graph Search:** Uses `GraphCypherQAChain` to dynamically query Neo4j using LLM-generated Cypher statements, securely retrieving multi-hop relationships.
- **FastAPI Backend:** A lightweight, async-first API for ingesting documents and performing complex queries.
- **Deduplicated Context:** Merges and deduplicates context from both vector and graph stores before passing it to the LLM for the final answer generation.

## Architecture & Tech Stack

- **Framework:** FastAPI, Uvicorn
- **Graph Database:** Neo4j (Local Desktop/Community Edition)
- **Vector Database:** FAISS (Local)
- **LLM Orchestration:** LangChain (`langchain`, `langchain_neo4j`, `langchain_community`)
- **LLM Provider:** OpenRouter (via `ChatOpenAI` client)
- **Embeddings:** HuggingFace (`BAAI/bge-m3`)

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd Knowledge-Graph-QA
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add the following keys:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_neo4j_password
   ```

5. **Start the Application:**
   ```bash
   uvicorn main:app --reload
   ```

## Usage

- **Ingestion:** Use the ingestion endpoints to upload PDFs. The system will chunk the text, extract the dynamic ontology, store embeddings in FAISS, and load nodes/relationships into Neo4j.
- **Retrieval:** Send queries to the retrieval endpoints. The system will leverage the Hybrid RAG pipeline to generate precise, context-aware answers based on the ingested graph and text.
