"""Retrieve graph-grounded COBOL context and synthesize modernization reports."""

import logging
from openai import OpenAI

logger = logging.getLogger("HybridSearchService")

# Keep the synthesis contract in one template so retrieved context and output
# requirements stay consistent across calls.
MODERNIZATION_PROMPT_TEMPLATE = """
You are a Principal Legacy Systems Architect and Senior Cloud Migration Engineer.
Analyze the following retrieved COBOL programs, copybooks, and JCL job dependencies from the graph database.

### Retrieved Context:
{context}

### Analysis Goal:
Provide a rigorous, developer-ready Technical Modernization & Refactoring Blueprint. Avoid generic advice. Focus exclusively on concrete code transformation, data contracts, and risk mitigation.

Your response must follow this exact markdown structure:

1. **System Architecture & Dependency Mapping**
   - Detail the caller/callee relationships between JCL jobs, COBOL programs (`CUSTUPD0`, `INTRCALC`), and shared copybooks (`CUSTREC`, `ACCTREC`).
   - Identify shared state variables or tight couplings.

2. **Business Logic Extraction**
   - Precisely document the conditional rules (e.g., VIP threshold logic, monthly interest compounding rates).

3. **Target Python/Microservice Blueprint**
   - Provide a clean, modern Python snippet (using Pydantic or FastAPI patterns) translating the core business rules of the legacy programs.

4. **Data Migration & Risk Strategy**
   - Outline database schema migration steps from fixed-width sequential files/VSAM to a modern relational/document store.
   - Note potential numerical truncation risks (e.g., PIC 9(07)V99).
"""

class HybridSearchService:
  """Combine semantic program matches with connected jobs and copybooks."""

  def __init__(self, driver, openai_client: OpenAI, settings):
    """Reuse the pipeline's database driver, model client, and active settings."""
    self.driver = driver
    self.openai_client = openai_client
    self.settings = settings

  def search_and_generate_report(self, user_query: str) -> str:
    """Retrieve relevant program context and synthesize a modernization plan."""
    # Query embeddings must use the same model as indexed program embeddings;
    # otherwise vector dimensions or embedding spaces may not be comparable.
    query_vector = (
        self.openai_client.embeddings.create(
            input=user_query, model=self.settings.embedding_model
        )
        .data[0]
        .embedding
    )

    # Optional matches retain a program result even when a job or copybook link
    # is absent, while the collections avoid repeating names in the prompt.
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

    # Keep graph retrieval separate from synthesis so the LLM receives concrete
    # code context instead of having to infer dependencies from the query alone.
    prompt = MODERNIZATION_PROMPT_TEMPLATE.format(context=combined_context)

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
