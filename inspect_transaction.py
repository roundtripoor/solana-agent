import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY is missing from .env")

if len(sys.argv) < 2:
    raise ValueError("Usage: python inspect_transaction.py <SIGNATURE>")

SIGNATURE = sys.argv[1]

URL = (
    f"https://api.helius.xyz/v0/transactions/"
    f"?api-key={HELIUS_API_KEY}"
)

response = requests.post(
    URL,
    json={
        "transactions": [SIGNATURE]
    },
    timeout=30,
)

print("=" * 60)
print("RAW TRANSACTION INSPECTION")
print("=" * 60)

print(f"HTTP status: {response.status_code}")
print(f"Requested signature: {SIGNATURE}")
print()

response.raise_for_status()

data = response.json()

# Save the transaction locally for participant_roles.py
transaction = data[0] if isinstance(data, list) else data

with open("last_transaction.json", "w", encoding="utf-8") as f:
    json.dump(transaction, f, indent=2)

print(json.dumps(data, indent=2))

print()
print("=" * 60)
print("Saved to: last_transaction.json")
print("END")
print("=" * 60)