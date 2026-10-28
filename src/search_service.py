import logging
from openai import OpenAI

logger = logging.getLogger("HybridSearchService")


class HybridSearchService:
  """Performs native Neo4j vector search combined with multi-hop graph traversal."""

  def __init__(self, driver, openai_client: OpenAI, settings):
    self.driver = driver
    self.openai_client = openai_client
    self.settings = settings

  def search_and_generate_report(self, user_query: str) -> str:
    # 1. Embed user query
    query_vector = (
        self.openai_client.embeddings.create(
            input=user_query, model=self.settings.embedding_model
        )
        .data[0]
        .embedding
    )

    # 2. Execute Hybrid Cypher Query
    cypher = """
        CALL db.index.vector.queryNodes('program_vectors', 3, $query_vector)
        YIELD node AS program, score
        OPTIONAL MATCH (job:Job)-[:EXECUTES]->(program)
        OPTIONAL MATCH (program)-[:USES_COPYBOOK]->(copybook:Copybook)
        RETURN 
            program.name AS ProgramName,
            program.business_logic AS BusinessLogic,
            score AS SimilarityScore,
            collect(DISTINCT job.name) AS ParentJobs,
            collect(DISTINCT copybook.name) AS DependentCopybooks
        """

    context_snippets = []
    with self.driver.session() as session:
      result = session.run(cypher, query_vector=query_vector)
      for record in result:
        snippet = (
            f"Program: {record['ProgramName']} (Score:"
            f" {record['SimilarityScore']:.4f})\nBusiness Logic:"
            f" {record['BusinessLogic']}\nTriggered By Jobs:"
            f" {record['ParentJobs']}\nUsed Copybooks:"
            f" {record['DependentCopybooks']}\n"
        )
        context_snippets.append(snippet)

    combined_context = "\n".join(context_snippets)

    # 3. Synthesize via LLM
    prompt = f"""
        You are an Enterprise Legacy Systems Architect. 
        Using the following hybrid graph-retrieved context from our mainframe repository, 
        write a formal Business Analysis & Modernization Report addressing: '{user_query}'.
        
        Context:
        {combined_context}
        
        Provide an Executive Summary, Core Business Rules, Data Lineage, and Modernization Advice.
        """

    completion = self.openai_client.chat.completions.create(
        model=self.settings.chat_model,
        messages=[
            {
                "role": "system",
                "content": "You write enterprise architecture reports.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return completion.choices[0].message.content
