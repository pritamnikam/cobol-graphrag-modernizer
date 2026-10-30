"""Remove Neo4j data and the vector index before a clean re-ingestion."""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables from .env
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def clean_neo4j():
  """Drop the program vector index and delete all nodes and relationships."""
  print(f"Connecting to Neo4j at {NEO4J_URI}...")
  driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

  with driver.session() as session:
    print("🗑️ Dropping existing vector index 'program_vectors'...")
    try:
      # The index may not exist on a fresh database; still proceed to clear
      # graph data so cleanup remains usable before the first ingestion.
      session.run("DROP INDEX program_vectors IF EXISTS")
      print("   Index dropped successfully.")
    except Exception as e:
      print(f"   Note on index drop: {e}")

    print("🗑️ Deleting all nodes and relationships...")
    # DETACH is required because the graph may contain relationships between
    # assets; delete everything to avoid mixing old and newly embedded data.
    session.run("MATCH (n) DETACH DELETE n")
    print("   All nodes and relationships deleted successfully.")

  driver.close()
  print("✨ Neo4j database is completely clean and ready for fresh ingestion!")


if __name__ == "__main__":
  # Keep destructive cleanup opt-in when the script is run directly.
  clean_neo4j()