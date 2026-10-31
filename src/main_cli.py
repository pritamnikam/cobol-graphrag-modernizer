"""Provide a text menu for the project's ingestion and analysis workflows."""

import os
import sys
from dotenv import load_dotenv

# Ensure the src directory is in path for imports if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


def print_banner():
  """Identify the tool and local-first execution mode in the interactive menu."""
  print("=" * 65)
  print("         COBOL GRAPHRAG MODERNIZER - INTERACTIVE CLI")
  print("         Privacy-First Local Pipeline via Docker Models")
  print("=" * 65)


def run_ingestion_pipeline():
  """Run the menu's ingestion action and display setup guidance on failure."""
  print(
      "\n🚀 [1] Running Full Ingestion, Vector Indexing & Modernization Report..."
  )
  try:
    from cobol_parser import CobolParserService  # Assuming your existing parser module
    from graph_repo import Neo4jGraphRepository  # Assuming your existing repo module

    print("Initializing parser and repository...")
    # Add your core ingestion logic here or import from your existing modules
    parser = CobolParserService()
    graph_repo = Neo4jGraphRepository()

    print("🌐 Using Docker Desktop Local Models via", os.getenv("LOCAL_AI_BASE_URL", "http://localhost:12434/engines/v1"))
    jobs, programs, copybooks = parser.parse_workspace("./cobol_source")
    print(f"Parsed successfully: {len(jobs)} Jobs, {len(programs)} Programs, {len(copybooks)} Copybooks.")

    graph_repo.ingest_and_index(jobs, programs, copybooks)
    print("✨ Graph ingestion and vector indexing completed successfully.")
    
  except Exception as e:
    print(f"❌ Error during ingestion: {e}")
    print("Tip: Make sure Neo4j is running and `script/setup_workspace.py` has been executed.")


def run_semantic_search():
  """Run the standalone vector-search smoke test from the menu."""
  print("\n🔍 [2] Running Semantic Vector Search Test...")
  try:
    from test_search import run_search
    run_search()
  except ImportError:
    # Fallback inline execution if test_search.py functions aren't exported
    os.system("python src/test_search.py")
  except Exception as e:
    print(f"❌ Error during search: {e}")


def run_capability_discovery():
  """Discover and tag the sample customer-finance capability."""
  print("\n🏷️ [3] Running Semantic Capability Discovery & Tagging...")
  try:
    from capability_discovery import CapabilityDiscoveryService

    cap_name = "Customer Financial Balance Management"
    cap_summary = (
        "This business capability manages customer accounts, evaluates yearly "
        "expenditures, updates VIP tier statuses, and computes monthly compound "
        "interest accruals. It relies on automated weekly billing cycles and "
        "monthly accounting runs to ensure ledger accuracy. The process "
        "interacts directly with customer master files and interest log records "
        "to maintain financial compliance and accurate tier-based benefits."
    )

    service = CapabilityDiscoveryService()
    service.discover_and_tag(cap_name, cap_summary)
  except Exception as e:
    print(f"❌ Error during capability discovery: {e}")


def run_capability_report():
  """Generate the report for the sample capability tagged by discovery."""
  print("\n📊 [4] Generating Capability Modernization Report...")
  try:
    from capability_report import CapabilityReportGenerator

    generator = CapabilityReportGenerator()
    generator.generate_report("Customer Financial Balance Management")
  except Exception as e:
    print(f"❌ Error during report generation: {e}")


def run_tri_hybrid_capability_discovery():
  """Fuse full-text, vector, and graph-structure capability rankings."""
  print("\n🔎 [5] Running Tri-hybrid Capability Discovery...")
  try:
    from capability_catalog import seed_capability_catalog
    from capability_discovery import CapabilityDiscoveryService

    query = input("\nDescribe the capability you want to find: ").strip()
    if not query:
      print("Enter a non-empty capability query.")
      return

    service = CapabilityDiscoveryService()
    print("Indexing the sample capability catalog...")
    seed_capability_catalog(service)
    matches = service.discover_capabilities(query, top_k=5)

    if not matches:
      print("No implemented capabilities matched the query.")
      return

    for rank, match in enumerate(matches, start=1):
      print(
          f"\n{rank}. {match['name']} "
          f"(RRF {match['rrf_score']:.4f}; "
          f"signals: {', '.join(match['matched_by'])})"
      )
      print(f"   {match['summary']}")
      print(
          "   Graph coverage: "
          f"{match['program_count']} programs, {match['job_count']} jobs, "
          f"{match['copybook_count']} copybooks"
      )
  except Exception as e:
    print(f"❌ Error during tri-hybrid capability discovery: {e}")


def main_menu():
  """Keep the CLI available for repeated operations until the user exits."""
  while True:
    print_banner()
    print("Please select an option:")
    print("  [1] Run Full Ingestion & Vector Indexing Pipeline")
    print("  [2] Run Semantic Vector Search Test")
    print("  [3] Discover & Tag Business Capabilities (Graph Enrichment)")
    print("  [4] Generate Capability Modernization Report (LLM Synthesis)")
    print("  [5] Tri-hybrid Capability Discovery")
    print("  [6] Exit")
    print("-" * 65)

    choice = input("Enter your choice (1-6): ").strip()

    # Dispatch one operation per selection; the final prompt gives the user
    # control over when the menu is redrawn.
    if choice == "1":
      run_ingestion_pipeline()
    elif choice == "2":
      run_semantic_search()
    elif choice == "3":
      run_capability_discovery()
    elif choice == "4":
      run_capability_report()
    elif choice == "5":
      run_tri_hybrid_capability_discovery()
    elif choice == "6":
      print("\n👋 Exiting Cobol GraphRAG Modernizer. Have a great day!")
      break
    else:
      print("❌ Invalid choice. Please enter a number between 1 and 6.")
    
    input("\nPress Enter to return to the main menu...")


if __name__ == "__main__":
  # Avoid starting interactive input when this module is imported elsewhere.
  main_menu()