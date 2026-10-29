import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()

class CapabilityReportGenerator:

  def __init__(self):
    self.openai_client = OpenAI(
        base_url=os.getenv(
            "LOCAL_AI_BASE_URL", "http://localhost:12434/engines/v1"
        ),
        api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
    )
    self.chat_model = os.getenv(
        "LOCAL_CHAT_MODEL", "hf.co/bartowski/llama-3.2-1b-instruct-gguf"
    )

    self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

  def generate_report(self, capability_name: str):
    print(
        f"\n📊 Fetching graph context for capability: '{capability_name}'..."
    )

    # Fetch all connected nodes for this capability from Neo4j
    cypher_query = """
        MATCH (cap:Capability {name: $cap_name})-[:DECOMPOSES_INTO]->(sub:SubCapability)-[:IMPLEMENTED_BY]->(prog:Program)
        OPTIONAL MATCH (job:Job)-[:EXECUTES]->(prog)
        OPTIONAL MATCH (prog)-[:USES_COPYBOOK]->(cb:Copybook)
        RETURN 
            cap.summary AS CapabilitySummary,
            sub.name AS SubCapability,
            prog.name AS ProgramName,
            prog.business_logic AS BusinessLogic,
            collect(DISTINCT job.name) AS Jobs,
            collect(DISTINCT cb.name) AS Copybooks
        """

    context_str = ""
    with GraphDatabase.driver(
        self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
    ) as driver:
      with driver.session() as session:
        result = session.run(cypher_query, {"cap_name": capability_name})
        for record in result:
          context_str += f"""
          - Sub-Capability: {record['SubCapability']}
          - Implementing Program: {record['ProgramName']}
          - Business Logic: {record['BusinessLogic']}
          - Associated JCL Jobs: {record['Jobs']}
          - Dependent Copybooks: {record['Copybooks']}
          """

    if not context_str:
      print(f"❌ No technical assets found tagged to capability '{capability_name}'. Run capability discovery first!")
      return

    print("Synthesizing Capability Modernization Report via Local LLM...")

    prompt = f"""
    You are a Principal Enterprise Cloud Architect. Analyze the following graph context for the business capability: '{capability_name}'.

    ### Capability Overview:
    {context_str}

    ### Objective:
    Produce an architectural migration blueprint proposing how to refactor these legacy mainframe assets into a modern domain-driven microservice (e.g., FastAPI / Python service). Include:
    1. **Domain Boundary Analysis** (What bounded context does this represent?)
    2. **API & Service Design** (Proposed endpoints replacing the JCL/COBOL execution flow)
    3. **Data Model Refactoring** (Converting copybook layouts into modern relational/JSON schemas)
    """

    response = self.openai_client.chat.completions.create(
        model=self.chat_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert enterprise modernization architect."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    report = response.choices[0].message.content
    print(f"\n================ CAPABILITY MODERNIZATION REPORT ================\n")
    print(report)
    print(f"\n==================================================================")


if __name__ == "__main__":
  generator = CapabilityReportGenerator()
  generator.generate_report("Customer Financial Balance Management")
