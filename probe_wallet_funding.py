import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY is missing from .env")

WALLET = "AjkDC1KdkgPaFRtrCbeSh6B6dhVX2JM4o2XhPSs2qu4b"

URL = (
    f"https://api.helius.xyz/v0/addresses/"
    f"{WALLET}/transactions"
    f"?api-key={HELIUS_API_KEY}"
)

response = requests.get(URL, timeout=30)

print("=" * 60)
print("WALLET FUNDING PROBE")
print("=" * 60)

print(f"Wallet: {WALLET}")
print(f"HTTP status: {response.status_code}")
print()

response.raise_for_status()

transactions = response.json()

print(f"Transactions returned: {len(transactions)}")
print()

for index, tx in enumerate(transactions[:30], start=1):

    timestamp = tx.get("timestamp")

    if timestamp:
        time_text = datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).isoformat()
    else:
        time_text = "UNKNOWN"

    print("-" * 60)
    print(f"#{index}")
    print(f"Time:        {time_text}")
    print(f"Signature:   {tx.get('signature')}")
    print(f"Type:        {tx.get('type')}")
    print(f"Source:      {tx.get('source')}")
    print(f"Fee payer:   {tx.get('feePayer')}")
    print(f"Description: {tx.get('description')}")

    native = tx.get("nativeTransfers", [])

    if native:
        print("Native transfers:")

        for transfer in native:
            print(
                f"  {transfer.get('fromUserAccount')} "
                f"-> "
                f"{transfer.get('toUserAccount')} "
                f"| "
                f"{transfer.get('amount')} lamports"
            )

print()
print("=" * 60)
print("END")
print("=" * 60)