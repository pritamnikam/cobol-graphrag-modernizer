"""Inspect the models exposed by a local Docker Model Runner endpoint."""

import json
import requests

# Query the OpenAI-compatible models route to verify local service readiness
# and see which model identifiers can be used by the pipeline.
url = "http://localhost:12434/engines/v1/models"

try:
  response = requests.get(url)
  print(f"Status Code: {response.status_code}")
  print("Raw JSON Response:")
  print(json.dumps(response.json(), indent=2))
except Exception as e:
  print(f"Failed to query models endpoint: {e}")