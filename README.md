# Cobol GraphRAG Modernizer

An enterprise-grade tool designed to automate the reverse-engineering of mainframe COBOL, JCL, and copybook assets into a **Neo4j Knowledge Graph** equipped with **Native Vector Indexing**. It bridges exact dependency tracing with semantic search to generate comprehensive business analysis and modernization reports via LLMs.

Supports **both** local privacy-first execution (via Docker Desktop's built-in Model Runner) and cloud execution (OpenAI).

---

## 🏗️ Architecture

1. **Parser Service:** Safely reads legacy files and extracts dependency relationships (`EXECUTES`, `USES_COPYBOOK`).
2. **Neo4j Storage:** Persists nodes and relationships while computing vector embeddings over business logic.
3. **Hybrid Search:** Combines semantic vector similarity search with index-free graph traversal.
4. **LLM Synthesis:** Feeds enriched multi-hop context into local or cloud models to produce actionable modernization documentation.

---

## 📋 Prerequisites

* **Python 3.10+**
* **Docker Desktop** (with Model Runner enabled for local models, or a running Neo4j instance)

---

## ⚙️ Configuration (`.env`)

In the root of your cloned repository, create a `.env` file based on your preferred execution provider.

### Option A: Local Docker Desktop Models (Default)
Docker Desktop's Model Runner exposes an OpenAI-compatible endpoint on port `12434` under `/engines/v1`.

```env
# --- Provider Switch ---
LLM_PROVIDER=docker

# --- Docker Desktop / Local Models Configuration ---
LOCAL_AI_BASE_URL=http://localhost:12434/engines/v1
LOCAL_AI_API_KEY=not-needed
LOCAL_CHAT_MODEL=hf.co/bartowski/llama-3.2-1b-instruct-gguf
LOCAL_EMBEDDING_MODEL=ai/embeddinggemma:latest

# --- Neo4j Database Configuration ---
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

```

### Option B: OpenAI Cloud Models

```env
# --- Provider Switch ---
LLM_PROVIDER=openai

# --- OpenAI Configuration ---
OPENAI_API_KEY=your-actual-api-key-here
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# --- Neo4j Database Configuration ---
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

```

---

## 🚀 Quick Start Guide

### Step 1: Start Neo4j via Docker

Spin up a local Neo4j instance using Docker:

```bash
docker run \
  --name neo4j-graphrag \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

```

*(Verify Neo4j is running by opening `http://localhost:7474` in your browser).*

### Step 2: Install Dependencies

Create a virtual environment, activate it, and install required packages:

```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate
# On macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt

```

### Step 3: Generate Mock COBOL Workspace

Populate sample JCL jobs, programs (`CUSTUPD0`, `INTRCALC`), and copybooks under `./cobol_source/`:

```bash
python script/setup_workspace.py

```

### Step 4: Run the Pipeline

Execute the main pipeline to parse assets, generate embeddings, build the Neo4j graph with native vector indexing, and output the modernization report:

```bash
python src/main.py

```

---

## 🔍 Visualizing the Graph in Neo4j Browser

1. Navigate to **`http://localhost:7474`** in your browser.
2. Log in with your credentials (`neo4j` / `password`).
3. Run the following Cypher query to explore your full legacy dependency graph:
```cypher
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m;

```



---

## 🛠️ Utility Maintenance Scripts

* **Clean Database & Indexes:** If you switch embedding models (e.g., changing vector dimensions between `768` and `1536`), run the cleanup utility before re-running the pipeline:
```bash
python scripts/clean_graph.py

```
