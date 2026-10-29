import os
from dotenv import load
from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings

load()

# Initialize embeddings pointing to your Docker local model
embeddings = OpenAIEmbeddings(
    base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
    model=os.getenv("LOCAL_EMBEDDING_MODEL", "ai/embeddinggemma:latest"),
    check_embedding_ctx_length=False,
)

# Connect to Neo4j
graph = Neo4jGraph(
    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password"),
)

# Load existing vector store
vector_store = Neo4jVector.from_existing_index(
    embedding=embeddings,
    url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password"),
    index_name="cobol_code_embeddings",  # Match your index name
    node_label="CodeChunk",
    text_node_property="text",
)

# Run a sample semantic search query
query = "Find COBOL code handling customer account balance calculation or interest"
results = vector_store.similarity_search(query, k=3)

print("--- Semantic Search Results ---")
for i, res in enumerate(results):
    print(f"\n[Result {i+1}]")
    print(res.page_content[:300])  # Print snippet of code/doc