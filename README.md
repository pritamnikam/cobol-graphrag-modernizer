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

---