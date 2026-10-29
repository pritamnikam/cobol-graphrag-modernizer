import json
import requests

# Correct Docker Model Runner OpenAI route path
url = "http://localhost:12434/engines/v1/models"

try:
  response = requests.get(url)
  print(f"Status Code: {response.status_code}")
  print("Raw JSON Response:")
  print(json.dumps(response.json(), indent=2))
except Exception as e:
  print(f"Failed to query models endpoint: {e}")