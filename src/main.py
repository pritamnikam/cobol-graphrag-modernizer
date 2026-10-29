# src/main.py
# The orchestration entry point that wires all the modules together with Docker/OpenAI switching.

import logging
import os
from graph_repo import Neo4jGraphRepository
from openai import OpenAI
from parser import CobolParserService
from pydantic_settings import BaseSettings
from search_service import HybridSearchService
from pydantic import ConfigDict

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MainPipeline")


class Settings(BaseSettings):
  model_config = ConfigDict(env_file=".env", extra="ignore")

  # --- Neo4j Configuration ---
  neo4j_uri: str = "bolt://127.0.0.1:7687"
  neo4j_user: str = "neo4j"
  neo4j_password: str = "password123"

  # --- Provider Switch: 'docker' vs 'openai' ---
  llm_provider: str = "docker"

  # --- Docker Desktop / Local Configuration ---
  local_ai_base_url: str = "http://localhost:12434/engines/v1"
  local_ai_api_key: str = "not-needed"
  local_chat_model: str = "hf.co/bartowski/llama-3.2-1b-instruct-gguf"
  local_embedding_model: str = "ai/embeddinggemma:latest"

  # --- OpenAI Configuration ---
  openai_api_key: str = "dummy-key"
  openai_chat_model: str = "gpt-4o"
  openai_embedding_model: str = "text-embedding-3-small"

  # --- Dynamic Aliases for Downstream Services ---
  @property
  def embedding_model(self) -> str:
    return (
        self.local_embedding_model
        if self.llm_provider.lower() == "docker"
        else self.openai_embedding_model
    )

  @property
  def chat_model(self) -> str:
    return (
        self.local_chat_model
        if self.llm_provider.lower() == "docker"
        else self.openai_chat_model
    )


settings = Settings()


if __name__ == "__main__":
  logger.info("Initializing Cobol GraphRAG Modernizer pipeline...")

  # --- CONDITIONAL LOGIC FOR CLIENT & MODEL SELECTION ---
  provider = settings.llm_provider.lower()

  if provider == "docker":
    logger.info(
        f"🌐 Using Docker Desktop Local Models via {settings.local_ai_base_url}"
    )
    openai_client = OpenAI(
        base_url=settings.local_ai_base_url, api_key=settings.local_ai_api_key
    )
    active_chat_model = settings.local_chat_model
    active_embedding_model = settings.local_embedding_model
  else:
    logger.info("☁️ Using OpenAI Cloud Models")
    openai_client = OpenAI(api_key=settings.openai_api_key)
    active_chat_model = settings.openai_chat_model
    active_embedding_model = settings.openai_embedding_model

  # 2. Initialize Neo4j Repository
  graph_repo = Neo4jGraphRepository(
      settings.neo4j_uri, (settings.neo4j_user, settings.neo4j_password)
  )

  try:
    # 3. Parse Workspace
    workspace_path = os.path.abspath("./cobol_source")
    parsed_workspace = CobolParserService.parse_workspace(workspace_path)

    # 4. Ingest into Neo4j with embeddings (using active dynamic model)
    graph_repo.ingest_graph_data(
        parsed_workspace, openai_client, active_embedding_model
    )

    # 5. Initialize Search Service & Run Analysis Query
    search_service = HybridSearchService(
        graph_repo.driver, openai_client, settings
    )
    report = search_service.search_and_generate_report(
        "How are customer balances evaluated and updated?"
    )

    print("\n================ GENERATED PRODUCTION REPORT ================")
    print(report)

  except Exception as e:
    logger.error(f"Pipeline execution failed: {str(e)}")
  finally:
    graph_repo.close()