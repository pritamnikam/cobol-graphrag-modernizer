import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()


class CapabilityDiscoveryService:

  def __init__(self):
    self.openai_client = OpenAI(
        base_url=os.getenv(
            "LOCAL_AI_BASE_URL", "http://localhost:12434/engines/v1"
        ),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
    )
    self.embedding_model = os.getenv(
        "LOCAL_EMBEDDING_MODEL", "ai/embeddinggemma:latest"
    )

    self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

  def discover_and_tag(
      self, capability_name: str, capability_summary: str, top_k: int = 3
  ):
    print(f"\n🔍 Analyzing Capability: '{capability_name}'...")

    # 1. Generate embedding for the capability summary
    print("Generating semantic embedding for summary...")
    response = self.openai_client.embeddings.create(
        input=capability_summary, model=self.embedding_model
    )
    capability_vector = response.data[0].embedding
    print(
        f"Embedding generated successfully! Dimensions:"
        f" {len(capability_vector)}"
    )

    # 2. Connect to Neo4j and execute semantic match + graph traversal tagging
    cypher_query = """
        // Step A: Find nearest program matches using vector index
        CALL db.index.vector.queryNodes('program_vectors', $k, $embedding)
        YIELD node AS program, score
        
        // Step B: Create or merge Capability & SubCapability nodes
        MERGE (cap:Capability {name: $cap_name})
        SET cap.summary = $cap_summary
        
        MERGE (sub:SubCapability {name: $sub_name})
        MERGE (cap)-[:DECOMPOSES_INTO]->(sub)
        
        // Step C: Tag the matched program and its connected neighborhood
        MERGE (sub)-[:IMPLEMENTED_BY]->(program)
        
        // Step D: Transition context with WITH before optional matching
        WITH sub, program, score
        OPTIONAL MATCH (job:Job)-[:EXECUTES]->(program)
        OPTIONAL MATCH (program)-[:USES_COPYBOOK]->(copybook:Copybook)
        
        RETURN 
            program.name AS Program, 
            score AS SemanticScore, 
            collect(DISTINCT job.name) AS LinkedJobs, 
            collect(DISTINCT copybook.name) AS LinkedCopybooks
    """

    sub_name = f"{capability_name} - Core Execution Flow"

    print("Executing Neo4j graph traversal and tagging...")
    with GraphDatabase.driver(
        self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
    ) as driver:
      with driver.session() as session:
        result = session.run(
            cypher_query,
            {
                "k": top_k,
                "embedding": capability_vector,
                "cap_name": capability_name,
                "cap_summary": capability_summary,
                "sub_name": sub_name,
            },
        )

        print(
            f"\n--- Capability Discovery Results for '{capability_name}' ---"
        )
        for record in result:
          print(f"\n📦 Program: {record['Program']} (Match Score: {record['SemanticScore']:.4f})")
          print(f"   - Linked JCL Jobs: {record['LinkedJobs'] if record['LinkedJobs'] else 'None'}")
          print(f"   - Linked Copybooks: {record['LinkedCopybooks'] if record['LinkedCopybooks'] else 'None'}")

    print(
        f"\n✨ Capability '{capability_name}' successfully mapped and tagged in"
        " Neo4j!"
    )


if __name__ == "__main__":
  # Example execution input
  sample_cap_name = "Customer Financial Balance Management"
  sample_cap_summary = (
      "This business capability manages customer accounts, evaluates yearly"
      " expenditures, updates VIP tier statuses, and computes monthly compound"
      " interest accruals. It relies on automated weekly billing cycles and"
      " monthly accounting runs to ensure ledger accuracy. The process"
      " interacts directly with customer master files and interest log records"
      " to maintain financial compliance and accurate tier-based benefits."
  )

  service = CapabilityDiscoveryService()
  service.discover_and_tag(sample_cap_name, sample_cap_summary)
