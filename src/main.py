import logging
import os
from openai import OpenAI
from pydantic_settings import BaseSettings
from graph_repo import Neo4jGraphRepository
from parser import CobolParserService
from search_service import HybridSearchService

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("MainPipeline")


class Settings(BaseSettings):
  neo4j_uri: str = "bolt://localhost:7687"
  neo4j_user: str = "neo4j"
  neo4j_password: str = "password123"
  openai_api_key: str = os.getenv("OPENAI_API_KEY", "dummy-key")
  embedding_model: str = "text-embedding-3-small"
  chat_model: str = "gpt-4o"

  class Config:
    env_file = ".env"
    extra = "ignore"


settings = Settings()


if __name__ == "__main__":
  logger.info("Initializing Cobol GraphRAG Modernizer pipeline...")

  # 1. Initialize OpenAI Client
  openai_client = OpenAI(api_key=settings.openai_api_key)

  # 2. Initialize Neo4j Repository
  graph_repo = Neo4jGraphRepository(
      settings.neo4j_uri, (settings.neo4j_user, settings.neo4j_password)
  )

  try:
    # 3. Parse Workspace
    workspace_path = os.path.abspath("./cobol_source")
    parsed_workspace = CobolParserService.parse_workspace(workspace_path)

    # 4. Ingest into Neo4j with embeddings
    graph_repo.ingest_graph_data(
        parsed_workspace, openai_client, settings.embedding_model
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