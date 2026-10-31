"""Unit tests for tri-hybrid ranking and capability search orchestration."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from src.capability_discovery import CapabilityDiscoveryService
from src.graph_repo import Neo4jGraphRepository


class CapabilityDiscoveryTests(unittest.TestCase):
  def setUp(self):
    self.openai_client = Mock()
    self.openai_client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
    )
    self.service = CapabilityDiscoveryService(
        openai_client=self.openai_client,
        embedding_model="test-embedding-model",
        neo4j_uri="bolt://test",
        neo4j_user="neo4j",
        neo4j_password="secret",
    )

  def test_rrf_combines_rankings_without_comparing_raw_scores(self):
    results = self.service.reciprocal_rank_fusion(
        {
            "lexical": [
                {"name": "Balance", "lexical_score": 1000},
                {"name": "Payments", "lexical_score": 0.1},
                {"name": "NoImplementation", "lexical_score": 2000},
            ],
            "semantic": [
                {"name": "Payments", "semantic_score": 0.99},
                {"name": "Balance", "semantic_score": 0.2},
            ],
            "heuristic": [
                {
                    "name": "Balance",
                    "program_count": 2,
                    "job_count": 3,
                    "copybook_count": 1,
                },
                {
                    "name": "Payments",
                    "program_count": 1,
                    "job_count": 1,
                    "copybook_count": 1,
                },
            ],
        },
        top_k=2,
        rrf_k=60,
    )

    self.assertEqual([item["name"] for item in results], ["Balance", "Payments"])
    self.assertAlmostEqual(
        results[0]["rrf_score"], (1 / 61) + (1 / 62) + (1 / 61)
    )
    self.assertEqual(results[0]["channel_ranks"], {
        "lexical": 1,
        "semantic": 2,
        "heuristic": 1,
    })
    self.assertEqual(results[0]["matched_by"], [
        "lexical",
        "semantic",
        "heuristic",
    ])
    self.assertEqual(results[0]["program_count"], 2)
    self.assertNotIn("NoImplementation", [item["name"] for item in results])

  def test_tri_hybrid_search_queries_each_channel_and_fuses_results(self):
    lexical = [
        {"name": "Balance", "summary": "Balances", "lexical_score": 8.0},
        {"name": "Payments", "summary": "Payments", "lexical_score": 2.0},
    ]
    semantic = [
        {"name": "Payments", "summary": "Payments", "semantic_score": 0.91},
        {"name": "Balance", "summary": "Balances", "semantic_score": 0.72},
    ]
    heuristic = [
        {
            "name": "Balance",
            "summary": "Balances",
            "program_count": 4,
            "job_count": 3,
            "copybook_count": 2,
        },
        {
            "name": "Payments",
            "summary": "Payments",
            "program_count": 2,
            "job_count": 1,
            "copybook_count": 1,
        },
    ]
    session = MagicMock()
    session.run.side_effect = [
        Mock(),  # full-text index creation
        Mock(),  # vector index creation
        Mock(),  # wait for index population
        lexical,
        semantic,
        heuristic,
    ]
    driver = MagicMock()
    driver.__enter__.return_value = driver
    driver.session.return_value.__enter__.return_value = session

    with patch(
        "src.capability_discovery.GraphDatabase.driver", return_value=driver
    ):
      results = self.service.discover_capabilities(
          "CUST-UPD balance? *", top_k=2
      )

    self.assertEqual([item["name"] for item in results], ["Balance", "Payments"])
    self.assertEqual(
        self.openai_client.embeddings.create.call_args.kwargs,
        {"input": "CUST-UPD balance? *", "model": "test-embedding-model"},
    )
    calls = session.run.call_args_list
    self.assertIn("CREATE FULLTEXT INDEX capability_text_index", calls[0].args[0])
    self.assertIn("CREATE VECTOR INDEX capability_vectors", calls[1].args[0])
    self.assertIn("db.awaitIndexes", calls[2].args[0])
    self.assertEqual(
        calls[3].args[1]["lexical_query"],
        '"CUST" OR "UPD" OR "balance"',
    )
    self.assertIn("coalesce(capability.status, 'ACTIVE')", calls[3].args[0])
    self.assertIn("program_count > 0", calls[5].args[0])

  def test_discovery_rejects_empty_queries_before_embedding(self):
    with self.assertRaisesRegex(ValueError, "must not be empty"):
      self.service.discover_capabilities("  ")
    self.openai_client.embeddings.create.assert_not_called()

  def test_discovery_rejects_queries_without_lexical_terms_before_embedding(self):
    with self.assertRaisesRegex(ValueError, "searchable terms"):
      self.service.discover_capabilities("?!")
    self.openai_client.embeddings.create.assert_not_called()

  def test_fusion_rejects_invalid_limits(self):
    with self.assertRaisesRegex(ValueError, "top_k"):
      self.service.reciprocal_rank_fusion({}, top_k=0)
    with self.assertRaisesRegex(ValueError, "rrf_k"):
      self.service.reciprocal_rank_fusion({}, rrf_k=0)

  def test_program_vector_index_uses_embedding_dimensions(self):
    repository = Neo4jGraphRepository.__new__(Neo4jGraphRepository)
    repository.driver = MagicMock()
    session = MagicMock()
    repository.driver.session.return_value.__enter__.return_value = session

    repository._create_vector_index(1536)

    create_index_query = session.run.call_args_list[0].args[0]
    self.assertIn("`vector.dimensions`: 1536", create_index_query)
    self.assertIn(
        "db.awaitIndexes", session.run.call_args_list[1].args[0]
    )


if __name__ == "__main__":
  unittest.main()
