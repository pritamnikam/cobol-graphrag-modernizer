import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()

# Initialize OpenAI client pointing to Docker Model Runner
openai_client = OpenAI(
    base_url=os.getenv("LOCAL_AI_BASE_URL", "http://localhost:12434/engines/v1"),
    api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
)

embedding_model = os.getenv("LOCAL_EMBEDDING_MODEL", "ai/embeddinggemma:latest")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Sample query text
query_text = (
    "Find COBOL code handling customer account balance calculation or interest"
)

print(f"Generating embedding for query: '{query_text}'...")
response = openai_client.embeddings.create(input=query_text, model=embedding_model)
query_vector = response.data[0].embedding

print(f"Query vector generated successfully! Dimensions: {len(query_vector)}")

cypher_query = """
CALL db.index.vector.queryNodes('program_vectors', $k, $embedding)
YIELD node, score
RETURN node.name AS name, node.business_logic AS logic, score
"""

print("\n--- Semantic Search Results ---")
# Using driver as a context manager ensures clean disposal before script exit
with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
  with driver.session() as session:
    result = session.run(cypher_query, {"k": 3, "embedding": query_vector})
    for i, record in enumerate(result):
      print(
          f"\n[Result {i+1}] Program: {record['name']} (Score:"
          f" {record['score']:.4f})"
      )
      print(record["logic"][:300] if record["logic"] else "No logic text")

print("\n✨ Search completed cleanly!")