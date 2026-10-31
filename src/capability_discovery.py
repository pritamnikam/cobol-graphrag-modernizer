"""Discover capabilities using lexical, semantic, and graph-based evidence."""

import os
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()


class CapabilityDiscoveryService:
  """Tag capabilities and rank them with reciprocal rank fusion."""

  def __init__(
      self,
      openai_client: Optional[OpenAI] = None,
      embedding_model: Optional[str] = None,
      neo4j_uri: Optional[str] = None,
      neo4j_user: Optional[str] = None,
      neo4j_password: Optional[str] = None,
  ):
    """Allow production defaults and injected clients for shared/test use."""
    provider = os.getenv("LLM_PROVIDER", "docker").lower()
    if openai_client is None:
      if provider == "docker":
        openai_client = OpenAI(
            base_url=os.getenv(
                "LOCAL_AI_BASE_URL", "http://localhost:12434/engines/v1"
            ),
            api_key=os.getenv("LOCAL_AI_API_KEY", "not-needed"),
        )
      elif provider == "openai":
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
      else:
        raise ValueError(
            "LLM_PROVIDER must be either 'docker' or 'openai'."
        )
    self.openai_client = openai_client
    self.embedding_model = embedding_model or os.getenv(
        "LOCAL_EMBEDDING_MODEL"
        if provider == "docker"
        else "OPENAI_EMBEDDING_MODEL",
        "ai/embeddinggemma:latest"
        if provider == "docker"
        else "text-embedding-3-small",
    )
    self.neo4j_uri = neo4j_uri or os.getenv(
        "NEO4J_URI", "bolt://127.0.0.1:7687"
    )
    self.neo4j_user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
    self.neo4j_password = neo4j_password or os.getenv(
        "NEO4J_PASSWORD", "password"
    )
    self._capability_index_dimensions = None

  @staticmethod
  def _ensure_capability_indexes(session, dimensions: int) -> None:
    """Create full-text and vector indexes required by the two retrieval arms."""
    session.run(
        """
        CREATE FULLTEXT INDEX capability_text_index IF NOT EXISTS
        FOR (c:Capability) ON EACH [c.name, c.summary]
        """
    ).consume()
    session.run(
        f"""
        CREATE VECTOR INDEX capability_vectors IF NOT EXISTS
        FOR (c:Capability)
        ON (c.embedding)
        OPTIONS {{ indexConfig: {{
          `vector.dimensions`: {dimensions},
          `vector.similarity_function`: 'cosine'
        }}}}
        """
    ).consume()
    # Neo4j builds schema indexes asynchronously; waiting avoids immediately
    # querying an index that was just created on a fresh database.
    session.run("CALL db.awaitIndexes($timeout_seconds)", timeout_seconds=300).consume()

  @staticmethod
  def _lexical_query(user_query: str) -> str:
    """Convert free text to quoted Lucene terms without passing operators."""
    terms = re.findall(r"[\w]+", user_query, flags=re.UNICODE)
    if not terms:
      raise ValueError("The discovery query must contain searchable terms.")
    return " OR ".join(f'"{term}"' for term in terms)

  @staticmethod
  def _record_dicts(records: Iterable[Any]) -> List[Dict[str, Any]]:
    """Normalize Neo4j records and plain mappings for fusion and unit tests."""
    return [
        record.data() if hasattr(record, "data") else dict(record)
        for record in records
    ]

  @staticmethod
  def reciprocal_rank_fusion(
      rankings: Mapping[str, Iterable[Mapping[str, Any]]],
      top_k: int = 5,
      rrf_k: int = 60,
  ) -> List[Dict[str, Any]]:
    """Fuse independently ranked result lists without mixing raw score scales."""
    if top_k <= 0:
      raise ValueError("top_k must be greater than zero.")
    if rrf_k <= 0:
      raise ValueError("rrf_k must be greater than zero.")

    fused: Dict[str, Dict[str, Any]] = {}
    for channel, records in rankings.items():
      for rank, record in enumerate(records, start=1):
        name = record.get("name")
        if not name:
          continue
        result = fused.setdefault(
            name,
            {
                "name": name,
                "summary": record.get("summary"),
                "rrf_score": 0.0,
                "channel_ranks": {},
                "matched_by": [],
                "lexical_score": None,
                "semantic_score": None,
                "program_count": 0,
                "job_count": 0,
                "copybook_count": 0,
            },
        )
        if record.get("summary"):
          result["summary"] = record["summary"]
        result["rrf_score"] += 1.0 / (rrf_k + rank)
        result["channel_ranks"][channel] = rank
        result["matched_by"].append(channel)

        if channel == "lexical":
          result["lexical_score"] = record.get("lexical_score")
        elif channel == "semantic":
          result["semantic_score"] = record.get("semantic_score")
        elif channel == "heuristic":
          for field in ("program_count", "job_count", "copybook_count"):
            result[field] = record.get(field, 0)

    eligible = [
        item
        for item in fused.values()
        if "heuristic" in item["matched_by"] and item["program_count"] > 0
    ]
    ordered = sorted(
        eligible,
        key=lambda item: (
            -item["rrf_score"],
            -item["program_count"],
            -item["job_count"],
            item["name"].casefold(),
        ),
    )
    return ordered[:top_k]

  def discover_and_tag(
      self, capability_name: str, capability_summary: str, top_k: int = 3
  ) -> None:
    """Find relevant programs and persist a searchable capability node."""
    if not capability_name.strip() or not capability_summary.strip():
      raise ValueError("Capability name and summary must not be empty.")
    if top_k <= 0:
      raise ValueError("top_k must be greater than zero.")

    response = self.openai_client.embeddings.create(
        input=capability_summary, model=self.embedding_model
    )
    capability_vector = response.data[0].embedding
    dimensions = len(capability_vector)
    if dimensions == 0:
      raise ValueError("The embedding service returned an empty capability vector.")

    cypher_query = """
        CALL db.index.vector.queryNodes('program_vectors', $k, $embedding)
        YIELD node AS program, score
        MERGE (cap:Capability {name: $cap_name})
        SET cap.summary = $cap_summary, cap.embedding = $embedding
        MERGE (sub:SubCapability {name: $sub_name})
        MERGE (cap)-[:DECOMPOSES_INTO]->(sub)
        MERGE (sub)-[:IMPLEMENTED_BY]->(program)
        WITH sub, program, score
        OPTIONAL MATCH (job:Job)-[:EXECUTES]->(program)
        OPTIONAL MATCH (program)-[:USES_COPYBOOK]->(copybook:Copybook)
        RETURN program.name AS Program,
               score AS SemanticScore,
               collect(DISTINCT job.name) AS LinkedJobs,
               collect(DISTINCT copybook.name) AS LinkedCopybooks
    """
    sub_name = f"{capability_name} - Core Execution Flow"

    with GraphDatabase.driver(
        self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
    ) as driver:
      with driver.session() as session:
        if self._capability_index_dimensions != dimensions:
          self._ensure_capability_indexes(session, dimensions)
          self._capability_index_dimensions = dimensions
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
        print(f"\n--- Capability Discovery Results for '{capability_name}' ---")
        for record in result:
          print(
              f"\n📦 Program: {record['Program']} "
              f"(Match Score: {record['SemanticScore']:.4f})"
          )
          print(f"   - Linked JCL Jobs: {record['LinkedJobs'] or 'None'}")
          print(
              f"   - Linked Copybooks: {record['LinkedCopybooks'] or 'None'}"
          )

  def discover_capabilities(
      self,
      user_query: str,
      top_k: int = 5,
      candidate_k: int = 20,
      rrf_k: int = 60,
  ) -> List[Dict[str, Any]]:
    """Rank existing capability nodes using lexical, vector, and graph signals.

    The heuristic list contains only capabilities connected to at least one
    implementing program. Explicitly deprecated capabilities are excluded in
    every retrieval arm; missing status is treated as active for older graphs.
    """
    if not user_query.strip():
      raise ValueError("The discovery query must not be empty.")
    if top_k <= 0 or candidate_k <= 0:
      raise ValueError("top_k and candidate_k must be greater than zero.")
    if rrf_k <= 0:
      raise ValueError("rrf_k must be greater than zero.")

    lexical_query = self._lexical_query(user_query)
    response = self.openai_client.embeddings.create(
        input=user_query, model=self.embedding_model
    )
    query_vector = response.data[0].embedding
    dimensions = len(query_vector)
    if dimensions == 0:
      raise ValueError("The embedding service returned an empty query vector.")

    lexical_cypher = """
        CALL db.index.fulltext.queryNodes(
            'capability_text_index', $lexical_query
        )
        YIELD node AS capability, score
        WHERE coalesce(capability.status, 'ACTIVE') <> 'DEPRECATED'
        RETURN capability.name AS name,
               capability.summary AS summary,
               score AS lexical_score
        ORDER BY lexical_score DESC
        LIMIT $candidate_k
    """
    semantic_cypher = """
        CALL db.index.vector.queryNodes(
            'capability_vectors', $candidate_k, $query_vector
        )
        YIELD node AS capability, score
        WHERE coalesce(capability.status, 'ACTIVE') <> 'DEPRECATED'
        RETURN capability.name AS name,
               capability.summary AS summary,
               score AS semantic_score
    """
    heuristic_cypher = """
        MATCH (capability:Capability)
        WHERE coalesce(capability.status, 'ACTIVE') <> 'DEPRECATED'
        OPTIONAL MATCH (capability)-[:DECOMPOSES_INTO]->
                       (:SubCapability)-[:IMPLEMENTED_BY]->(program:Program)
        OPTIONAL MATCH (job:Job)-[:EXECUTES]->(program)
        OPTIONAL MATCH (program)-[:USES_COPYBOOK]->(copybook:Copybook)
        WITH capability,
             count(DISTINCT program) AS program_count,
             count(DISTINCT job) AS job_count,
             count(DISTINCT copybook) AS copybook_count
        WHERE program_count > 0
        RETURN capability.name AS name,
               capability.summary AS summary,
               program_count,
               job_count,
               copybook_count
        ORDER BY program_count DESC, job_count DESC, copybook_count DESC,
                 name ASC
        LIMIT $candidate_k
    """

    with GraphDatabase.driver(
        self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
    ) as driver:
      with driver.session() as session:
        if self._capability_index_dimensions != dimensions:
          self._ensure_capability_indexes(session, dimensions)
          self._capability_index_dimensions = dimensions

        # Materialize each list before issuing the next query; RRF needs each
        # channel's independent ordering rather than an index join/intersection.
        lexical = self._record_dicts(session.run(
            lexical_cypher,
            {"lexical_query": lexical_query, "candidate_k": candidate_k},
        ))
        semantic = self._record_dicts(session.run(
            semantic_cypher,
            {"query_vector": query_vector, "candidate_k": candidate_k},
        ))
        heuristic = self._record_dicts(session.run(
            heuristic_cypher, {"candidate_k": candidate_k}
        ))

    return self.reciprocal_rank_fusion(
        {
            "lexical": lexical,
            "semantic": semantic,
            "heuristic": heuristic,
        },
        top_k=top_k,
        rrf_k=rrf_k,
    )


if __name__ == "__main__":
  sample_cap_name = "Customer Financial Balance Management"
  sample_cap_summary = (
      "This business capability manages customer accounts, evaluates yearly "
      "expenditures, updates VIP tier statuses, and computes monthly compound "
      "interest accruals. It relies on automated weekly billing cycles and "
      "monthly accounting runs to ensure ledger accuracy."
  )

  service = CapabilityDiscoveryService()
  service.discover_and_tag(sample_cap_name, sample_cap_summary)
