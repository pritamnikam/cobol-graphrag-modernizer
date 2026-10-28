# Cobol GraphRAG Modernizer

An enterprise-grade tool designed to automate the reverse-engineering of mainframe COBOL, JCL, and copybook assets into a **Neo4j Knowledge Graph** equipped with **Native Vector Indexing**. It bridges exact dependency tracing with semantic search to generate comprehensive business analysis reports via LLMs.

## Architecture
1. **Parser Service:** Safely reads legacy files and extracts dependency relationships (`EXECUTES`, `USES_COPYBOOK`).
2. **Neo4j Storage:** Persists nodes and relationships while computing vector embeddings over business logic.
3. **Hybrid Search:** Combines semantic vector similarity search with index-free graph traversal.
4. **LLM Synthesis:** Feeds enriched multi-hop context into GPT-4o to produce actionable modernization documentation.

## Quick Start
1. Clone the repository and configure your environment variables:

```bash
cp .env.example .env

# Start Neo4j via Docker Compose:
docker compose up -d

# Install dependencies:
pip install -r requirements.txt

# Generate Mock Data:
python scripts/setup_workspace.py

# Run the pipeline:
export OPENAI_API_KEY="your-actual-api-key"
python src/main.py

```



To run **`cobol-graphrag-modernizer`** locally using your Docker Desktop models (`ai/smollm2:360M-Q4_K_M`, `hf.co/bartowski/llama-3.2-1b-instruct-gguf`, and `ai/embeddinggemma:latest`) with the flexibility to switch to OpenAI, we can introduce configuration flags via environment variables (typically structured inside a `.env` file or configuration loader).

Here is a step-by-step guide to configure the environment switches, spin up Neo4j, seed the COBOL demo data, and verify semantic search against your local models.

---

### Step 1: Set Up Your Environment Variables (`.env`)

In the root of your cloned repository, create or update your `.env` file to include provider switches for both the LLM and the embedding model.

*Note: Docker Desktop local models are typically exposed via an OpenAI-compatible API endpoint (such as Ollama, LocalAI, or Docker AI extensions) usually running on `http://localhost:11434/v1` or `http://localhost:8000/v1`.*

```env
# Choose your provider: 'docker' (or 'openai-compatible') vs 'openai'
LLM_PROVIDER=docker
EMBEDDING_PROVIDER=docker

# --- Docker Desktop / Local Models Configuration ---
# Point to your local server running the Docker models (adjust port if needed, e.g., 11434 for Ollama)
LOCAL_AI_BASE_URL=http://localhost:11434/v1
LOCAL_AI_API_KEY=not-needed

# Select which local model to use from your Docker desktop inventory
LOCAL_LLM_MODEL=hf.co/bartowski/llama-3.2-1b-instruct-gguf
# Alternatively: LOCAL_LLM_MODEL=ai/smollm2:360M-Q4_K_M

LOCAL_EMBEDDING_MODEL=ai/embeddinggemma:latest

# --- OpenAI Configuration (For switching back) ---
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# --- Neo4j Database Configuration ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

```

---

### Step 2: Incorporate the Switch in Your Codebase

To allow your Python code to dynamically switch between Docker-hosted local models and OpenAI, update your LLM/Embedding client initialization file (e.g., `config.py`, `database.py`, or wherever `ChatOpenAI` / `OpenAIEmbeddings` from LangChain or standard OpenAI clients are instantiated).

Here is how you can implement the conditional logic:

```python
import os
from dotenv import load

load()

llm_provider = os.getenv("LLM_PROVIDER", "docker").lower()
embedding_provider = os.getenv("EMBEDDING_PROVIDER", "docker").lower()

# --- LLM Initialization ---
if llm_provider == "docker":
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
        model=os.getenv(
            "LOCAL_LLM_MODEL", "hf.co/bartowski/llama-3.2-1b-instruct-gguf"
        ),
    )
else:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"),
    )

# --- Embedding Initialization ---
if embedding_provider == "docker":
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
        model=os.getenv("LOCAL_EMBEDDING_MODEL", "ai/embeddinggemma:latest"),
        # Note: Some local embedding endpoints require disabling check for dimensions
        check_embedding_ctx_length=False,
    )
else:
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )

```

---

### Step 3: Run Neo4j via Docker

If you aren't already running Neo4j, spin up a local instance using Docker:

```bash
docker run \
  --name neo4j-graphrag \
  -p7687:7687 -p7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

```

Verify Neo4j is running by opening `http://localhost:7474` in your browser and logging in with `neo4j` / `password`.

---

### Step 4: Install Dependencies & Seed the Data

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt

```


2. **Seed the COBOL Demo Data into Neo4j:**
Look for the ingestion/seeding script in your repository (typically named something like `seed.py`, `ingest.py`, or `main.py --ingest`). Run it to parse the sample COBOL code, generate embeddings using your local `embeddinggemma` model, and populate the Neo4j knowledge graph:
```bash
python seed.py

```


*(Check your project's `README.md` or file structure for the exact script name if it differs).*

---

### Step 5: Verify Semantic Search & Graph RAG Execution

Once the data is successfully seeded and connected to your local model stack (`llama-3.2-1b` or `smollm2` for generation + `embeddinggemma` for vector embeddings), run your query pipeline or app interface:

```bash
python main.py
# or if it has a web/streamlit UI:
streamlit run app.py

```

1. Go to the Neo4j Browser (`http://localhost:7474`) and execute a quick Cypher query to verify nodes and vector indexes are populated:
```cypher
MATCH (n) RETURN n LIMIT 25;

```


2. Test a semantic query through your application prompt to ensure retrieval traverses the graph and returns insights processed by your local Docker models.
