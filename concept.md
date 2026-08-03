# Knowledge Graphs & GraphRAG: Comprehensive Core Concepts & Implementation Guide

This reference document synthesizes the foundational concepts, design patterns, chunking/retrieval strategies, and architectural paradigms learned while building this enterprise **GraphRAG (Knowledge Graph + Retrieval-Augmented Generation)** system.

---

## 1. Introduction: From Traditional RAG to GraphRAG

### 1.1 Limitations of Traditional Vector RAG
Standard Retrieval-Augmented Generation (RAG) relies primarily on **Dense Vector Search** (e.g., embedding document chunks into a vector space using FAISS, Chroma, or Pinecone and computing cosine/L2 distance). 

While vector search excels at **flat semantic matching**, it suffers from major architectural limitations:
1. **Lack of Multi-Hop Reasoning**: Vector search cannot traverse indirect relationships (e.g., *If Document A connects Entity X to Entity Y, and Document B connects Entity Y to Entity Z, vector search fails to infer the link between X and Z*).
2. **Loss of Structural Context**: Chunking text into static windows breaks relational context across sentence boundaries and paragraphs.
3. **No Entity Resolution / Deduplication**: Mentioning "Cardiometabolic Disease" in Chunk 1 and "Cardiometabolic Disorder" in Chunk 50 treats them as distinct vectors rather than unified concepts.
4. **Poor Global Summarization**: Answering high-level corpus questions (*"What are the recurring risk factors across all patient reports?"*) fails because no single chunk contains the complete answer.

### 1.2 The GraphRAG Paradigm
**GraphRAG** bridges dense vector search with structured graph databases (e.g., Neo4j). By extracting entities and explicit semantic relationships, GraphRAG converts unstructured text into a multi-dimensional knowledge network.

```
+-----------------------------------------------------------------------------------+
|                                 HYBRID RAG PIPELINE                               |
|                                                                                   |
|   +-----------------------+                         +-------------------------+   |
|   |   Unstructured PDF    |                         |    User Natural Query   |   |
|   +-----------+-----------+                         +------------+------------+   |
|               |                                                  |                |
|               v                                                  v                |
|   +-----------+-----------+                         +------------+------------+   |
|   | Chunking & Processing |                         |   Hybrid Retrieval Engine   |   |
|   +-----+-----------+-----+                         +-----+-------------+-----+   |
|         |           |                                     |             |         |
|         v           v                                     v             v         |
|   +-----+---+   +---+-----+                         +-----+---+   +-----+-----+   |
|   |  FAISS  |   | Neo4j   |                         | Vector  |   | Graph     |   |
|   | Vector  |   | Graph   |<=======================>| Search  |   | Search    |   |
|   | Store   |   | Database|                         | (FAISS) |   | (Cypher)  |   |
|   +---------+   +---------+                         +----+----+   +-----+-----+   |
|                                                          |              |         |
|                                                          +------+-------+         |
|                                                                 |                 |
|                                                                 v                 |
|                                                     +-----------+-----------+     |
|                                                     | Context Fusion & LLM  |     |
|                                                     | Generation (Explain)  |     |
|                                                     +-----------------------+     |
+-----------------------------------------------------------------------------------+
```

---

## 2. Knowledge Representation: TBox vs. ABox

Knowledge graphs divide domain knowledge into two distinct logical layers derived from Description Logics (DL):

```
       +--------------------------------------------------+
       |               TBox (Terminological)              |
       |  Schema, Entity Classes, Relationship Taxonomies |
       |  e.g., (:Disease)-[:HAS_SYMPTOM]->(:Symptom)     |
       +------------------------+-------------------------+
                                | Instantiates
                                v
       +--------------------------------------------------+
       |                ABox (Assertional)                |
       |  Concrete Instances, Properties, & Explicit Facts|
       |  e.g., ("Diabetes")-[:HAS_SYMPTOM]->("Polyuria") |
       +--------------------------------------------------+
```

### 2.1 TBox (Terminological Box / Schema Layer)
- Defines the **ontology, node labels, relationship types, and domain constraints**.
- Controls structural integrity and prevents LLMs from inventing arbitrary relationship names during extraction.
- **Example in our system**:
  - Node Labels: `Document`, `Chunk`, `Entity`
  - Entity Types (`type` property): `Disease`, `Treatment`, `Symptom`, `RiskFactor`, `Vendor`, `Location`
  - Relationship Types: `HAS_CHUNK`, `MENTIONS`, `HAS_SYMPTOM`, `TREATED_BY`, `COMORBID_WITH`, `AFFECTS`

### 2.2 ABox (Assertional Box / Instance Layer)
- Contains the **actual data instances and facts** extracted from documents.
- Represents specific entities and their explicit connections.
- **Example in our system**:
  - `(d:Document {filename: "ai_rag_notes.pdf"})-[:HAS_CHUNK]->(c:Chunk {chunk_id: "ai_rag_notes.pdf_chunk_0"})`
  - `(c:Chunk)-[:MENTIONS]->(e1:Entity {name: "Hypertension", type: "Disease"})`
  - `(e1:Entity {name: "Hypertension"})-[:TREATED_BY]->(e2:Entity {name: "ACE Inhibitors", type: "Treatment"})`

---

## 3. Knowledge Graph Ingestion Techniques

Modern GraphRAG architectures utilize three primary strategies for knowledge graph ingestion:

### Technique 1: LLM-Driven Zero-Shot / Few-Shot Information Extraction (IE)
- **Mechanism**: Passes raw text chunks to an LLM paired with structured JSON / Pydantic response schemas.
- **Pros**: Dynamic, handles unexpected domain concepts gracefully.
- **Cons**: Prone to relationship hallucination and entity duplicate creation if unconstrained.

### Technique 2: Ontology-Guided Schema Extraction (Implemented Strategy)
- **Mechanism**: The extraction prompt specifies allowable entity classes (`Disease`, `Treatment`, `Symptom`, etc.) and strict relationship taxonomies.
- **Pydantic Schema Pattern**:
  ```python
  class Entity(BaseModel):
      name: str
      type: str  # Disease, Symptom, Treatment, etc.

  class Relationship(BaseModel):
      source: str
      target: str
      relation_type: str  # HAS_SYMPTOM, TREATED_BY, etc.
  ```

### Technique 3: Pipeline Parallelism & Atomic Merging (`MERGE` Cypher Pattern)
- **Mechanism**: To ingest multi-page documents without duplicate node creation, ingestion uses atomic Cypher `MERGE` queries:
  ```cypher
  // Ensure entity node uniqueness across documents
  MERGE (e:Entity {name: $entity_name})
  ON CREATE SET e.type = $entity_type
  ```
- **Hierarchical Provenance**: Every entity is linked back to its originating `Chunk` and `Document`, enabling exact citation tracing.

---

## 4. Chunking Strategies for Knowledge Bases & Graph Building

Chunking dictates the resolution at which semantic concepts and relationships are captured.

| Chunking Strategy | Description | Best Used For | Trade-offs |
| :--- | :--- | :--- | :--- |
| **Fixed-Size Chunking** | Splits text at strict character boundaries (e.g., 500 chars). | Baseline benchmarks, fast processing. | Cuts entities and relationships in half across boundary lines. |
| **Recursive Character Chunking** *(Implemented)* | Splits text using a hierarchy of separators (`\n\n`, `\n`, ` `, `""`) with overlap. | General document RAG, preserving sentence structure. | Requires tuned chunk size (e.g., 1000 chars, 200 overlap) to balance context vs LLM extraction limits. |
| **Semantic Chunking** | Computes sentence embedding distances and splits when semantic similarity drops. | Narrative texts, unstructured essays. | Higher latency during ingestion due to continuous embedding calculations. |
| **Graph-Native / Structural Chunking** | Uses Markdown headings, tables, or sections as natural boundaries. | Technical docs, structured PDFs, API manuals. | Variable chunk sizes; requires parsing document layouts. |

### Impact of Chunk Size on Graph Construction:
- **Too Small (< 300 chars)**: Fails to capture multi-entity relationships (*"Drug X was prescribed to Patient Y who presented with Condition Z"* gets split across 3 chunks).
- **Too Large (> 2500 chars)**: Overwhelms LLM extraction prompts, leading to missed entities and lower precision.
- **Optimal Range**: **800–1200 characters with 150–200 character overlap**.

---

## 5. Retrieval Strategies: Graph Search, Vector Search & Context Fusion

```
                       +-----------------------------------+
                       |           User Query              |
                       +-----------------+-----------------+
                                         |
                        +----------------+----------------+
                        |                                 |
                        v                                 v
        +---------------+---------------+  +--------------+----------------+
        |   FAISS Vector Similarity     |  |   Text-to-Cypher Graph Search   |
        |   (Dense Semantic Retrieval)  |  |   (Multi-Hop Path Traversal)   |
        +---------------+---------------+  +--------------+----------------+
                        |                                 |
                        | Top-K Chunks                    | Multi-Hop Paths
                        +----------------+----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       |         Context Fusion Engine     |
                       |  Assembles Semantic + Relational  |
                       |  Context into LLM Prompt          |
                       +-----------------+-----------------+
                                         |
                                         v
                       +-----------------+-----------------+
                       |      Grounded Generation &        |
                       |      Explainable Citations        |
                       +-----------------------------------+
```

### 5.1 Dense Vector Search (FAISS)
- Converts queries to embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
- Performs similarity search over text chunks.
- **Metadata Filter Support**: Supports local scoping via `filter={"source": filename}`.

### 5.2 Text-to-Cypher Graph Search (`GraphCypherQAChain`)
- Dynamic text-to-graph retrieval translates natural language into executable Cypher queries.
- Bypasses traditional APOC plugin dependencies by injecting dynamic schema definitions (`graph.schema`).
- Automatically extracts multi-hop paths (`MATCH (a:Entity)-[r]->(b:Entity)...`).

### 5.3 Local Search vs. Global Search Paradigms
- **Local Search (Document-Scoped)**:
  - User selects a specific document (`filename`).
  - *Vector Filter*: `filter={"source": "ai_rag_notes.pdf"}`
  - *Cypher Rule*: Injects `MATCH (d:Document {filename: '...'})-[:HAS_CHUNK]->(c)-[:MENTIONS]->(e)` into the prompt.
  - *Benefit*: High precision, zero cross-document noise.
- **Global Search (Corpus-Wide)**:
  - User selects `Global (All Documents)`.
  - Removes metadata constraints, allowing the graph chain to traverse cross-document entity linkages.

### 5.4 Context Fusion
The `assemble_context()` function combines vector snippets and graph paths into a structured prompt:
```markdown
### Semantic Context from Documents ###
Source: ai_rag_notes.pdf (Page 1)
Text: Hypertension is a primary risk factor for cardiometabolic disorders...

### Relational Context from Knowledge Graph (Multi-Hop Paths) ###
(:Entity {name: 'Hypertension', type: 'Disease'})-[:HAS_RISK_FACTOR]->(:Entity {name: 'Obesity', type: 'RiskFactor'})
```

---

## 6. Recommendation Systems Using Knowledge Graphs & ML

Knowledge graphs are extensively used in modern recommendation engines to combat the **Cold-Start Problem** and **Sparsity**.

### Key Paradigms:
1. **Knowledge Graph Embeddings (KGE)**:
   - Algorithms like **TransE, RotatE, Complex** translate entities and relations into low-dimensional vector spaces where $h + r \approx t$ (Head + Relation $\approx$ Tail).
2. **Graph Neural Networks (GNNs / GraphSAGE / LightGCN)**:
   - Propagate features across multi-hop node neighborhoods to learn high-order user-item representations.
3. **Path-Based Explainable Recommendations**:
   - Computes explicit meta-paths (e.g., `User -> Bought -> Item A -> Shares_Vendor -> Item B`) to explain *why* an item was recommended.

---

## 7. Complete System Architecture of This Codebase

```
+-------------------------------------------------------------------------------------+
|                                 GRAPH-QA ARCHITECTURE                               |
|                                                                                     |
|  [ FRONTEND - Streamlit (ui.py) ]                                                   |
|  ├── Ingestion Page (Upload PDF, Processing Polling, SQLite History Panel)          |
|  ├── Knowledge Graph Visualizer (Interactive PyVis/agraph, Dynamic Node Side-Panel)|
|  └── Chat & Q&A (Explorer, Local/Global Dropdown, Inference Path & Source Pills)   |
|                                                                                     |
|  [ BACKEND - FastAPI (main.py) ]                                                    |
|  ├── /documents/upload & /documents/history (PDF Ingestion & SQLite Audit)          |
|  ├── /graph/visualize/{filename} (Neo4j Node/Edge Serialization)                    |
|  └── /qa/ask (Hybrid Search, Cypher Generation, Grounded LLM Response)              |
|                                                                                     |
|  [ PERSISTENCE & STORAGE LAYER ]                                                    |
|  ├── Neo4j Database (Graph Storage: Document, Chunk, Entity nodes)                 |
|  ├── FAISS Vector Index (Dense Chunk Embeddings & Metadata)                         |
|  └── SQLite Database (app.db: Persistent Ingestion Audit Logs)                      |
+-------------------------------------------------------------------------------------+
```

---

## 8. Summary of Key Implementation Lessons

1. **Avoid Hardcoded Cypher Schemas**: Dynamic schema injection ensures the LLM generates valid Cypher statements aligned with current graph data.
2. **Double Escaping in Prompt Templates**: When constructing LangChain `PromptTemplate` objects inside Python `f-strings`, escape template placeholders (`{{question}}`) to prevent `NameError` exceptions during runtime evaluation.
3. **Atomic Neo4j Merges**: Always use `MERGE` statements with parameter bindings to prevent entity duplication during multi-document ingestion.
4. **Transparent AI / Explainability**: Exposing the **Inference Path (Cypher query)** and **Source Citations** builds user trust and makes debugging RAG pipelines fast and deterministic.
