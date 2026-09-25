import os
import requests
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY is missing from .env")

import sys

if len(sys.argv) < 2:
    raise ValueError("Usage: python probe_token_history.py <TOKEN_MINT>")

TOKEN_MINT = sys.argv[1]

URL = (
    f"https://api.helius.xyz/v0/addresses/"
    f"{TOKEN_MINT}/transactions"
    f"?api-key={HELIUS_API_KEY}"
)

response = requests.get(URL, timeout=30)

print("=" * 60)
print("TOKEN HISTORY PROBE")
print("=" * 60)

print(f"Token: {TOKEN_MINT}")
print(f"HTTP status: {response.status_code}")
print()

response.raise_for_status()

transactions = response.json()

print(f"Transactions returned: {len(transactions)}")
print()

for index, tx in enumerate(transactions[:20], start=1):
    print("-" * 60)
    print(f"#{index}")
    print(f"Signature:     {tx.get('signature')}")
    print(f"Timestamp:     {tx.get('timestamp')}")
    print(f"Type:          {tx.get('type')}")
    print(f"Source:        {tx.get('source')}")
    print(f"Fee payer:     {tx.get('feePayer')}")
    print(f"Description:   {tx.get('description')}")
    print(f"Slot:          {tx.get('slot')}")

print()
print("=" * 60)
print("END")
print("=" * 60)