"""Seed the sample capability catalog and query it with tri-hybrid ranking."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from src.capability_catalog import seed_capability_catalog
from src.capability_discovery import CapabilityDiscoveryService


def main() -> None:
  """Tag the sample capabilities, then print ranked query matches."""
  query = input(
      "\nDescribe the business capability you want to find: "
  ).strip()
  if not query:
    print("Enter a non-empty capability query.")
    return

  service = CapabilityDiscoveryService()
  seed_capability_catalog(service)
  results = service.discover_capabilities(query, top_k=5)

  if not results:
    print("No implemented capabilities matched the query.")
    return

  print("\n--- Tri-hybrid capability matches ---")
  for rank, result in enumerate(results, start=1):
    channels = ", ".join(result["matched_by"])
    print(
        f"\n{rank}. {result['name']} "
        f"(RRF: {result['rrf_score']:.4f}; matched by: {channels})"
    )
    print(f"   {result['summary']}")
    print(
        "   Graph coverage: "
        f"{result['program_count']} programs, {result['job_count']} jobs, "
        f"{result['copybook_count']} copybooks"
    )


if __name__ == "__main__":
  main()
