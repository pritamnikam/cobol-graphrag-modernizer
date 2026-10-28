import logging
from typing import Any, Dict, List
from neo4j import GraphDatabase
from openai import OpenAI

logger = logging.getLogger("Neo4jGraphRepository")


class Neo4jGraphRepository:
  """Handles database connectivity, schema constraints, and batch data loading."""

  def __init__(self, uri: str, auth: tuple):
    self.driver = GraphDatabase.driver(uri, auth=auth)
    self._initialize_schema()

  def close(self):
    self.driver.close()

  def _initialize_schema(self):
    """Sets unique constraints."""
    queries = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Job) REQUIRE j.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Program) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Copybook) REQUIRE c.name IS UNIQUE",
    ]
    with self.driver.session() as session:
      for q in queries:
        session.run(q)
    logger.info("Neo4j constraints verified/created.")

  def ingest_graph_data(
      self,
      data: Dict[str, List[Dict[str, Any]]],
      openai_client: OpenAI,
      embedding_model: str,
  ):
    """Batches data ingestion and computes vector embeddings for programs."""
    with self.driver.session() as session:
      # Ingest Jobs
      for job in data["jobs"]:
        session.run(
            "MERGE (j:Job {name: $name}) SET j.code = $code, j.datasets ="
            " $datasets",
            {
                "name": job["name"],
                "code": job["code"],
                "datasets": str(job["datasets"]),
            },
        )

      # Ingest Programs & Compute Embeddings
      for prog in data["programs"]:
        response = openai_client.embeddings.create(
            input=prog["business_logic"], model=embedding_model
        )
        embedding = response.data[0].embedding

        session.run(
            """
                MERGE (p:Program {name: $name}) 
                SET p.code = $code, 
                    p.business_logic = $logic, 
                    p.embedding = $embedding
                """,
            {
                "name": prog["name"],
                "code": prog["code"],
                "logic": prog["business_logic"],
                "embedding": embedding,
            },
        )

      # Ingest Copybooks
      for cpy in data["copybooks"]:
        session.run(
            "MERGE (c:Copybook {name: $name}) SET c.code = $code",
            {"name": cpy["name"], "code": cpy["code"]},
        )

      # Ingest Relationships
      for rel in data["relations"]:
        cypher = f"""
                MATCH (a {{name: $from_name}})
                MATCH (b {{name: $to_name}})
                MERGE (a)-[r:{rel['rel']}]->(b)
                """
        session.run(cypher, {"from_name": rel["from"], "to_name": rel["to"]})

    self._create_vector_index()
    logger.info("Graph ingestion and vector indexing completed successfully.")

  def _create_vector_index(self):
    query = """
        CREATE VECTOR INDEX program_vectors IF NOT EXISTS
        FOR (p:Program) 
        ON (p.embedding)
        OPTIONS { indexConfig: {
          `vector.dimensions`: 1536,
          `vector.similarity_function`: 'cosine'
        }}
        """
    with self.driver.session() as session:
      session.run(query)
