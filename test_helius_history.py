import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY")

if not api_key:
    raise ValueError("HELIUS_API_KEY is missing from .env")

address = "8V4kM8JEGa4godgzbvAksQUtMNJ9GyPCxKqS6vUFTf72"

url = f"https://api.helius.xyz/v0/addresses/{address}/transactions"

response = requests.get(
    url,
    params={
        "api-key": api_key,
        "limit": 20,
    },
)

print("HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit

transactions = response.json()

print(f"\nFound {len(transactions)} transactions\n")
print("=" * 80)

for tx in transactions:
    timestamp = tx.get("timestamp")

    if timestamp:
        time = datetime.fromtimestamp(
            timestamp, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        time = "unknown"

    print(f"Time:        {time}")
    print(f"Type:        {tx.get('type')}")
    print(f"Description: {tx.get('description')}")
    print(f"Signature:   {tx.get('signature')}")

    token_transfers = tx.get("tokenTransfers", [])
    native_transfers = tx.get("nativeTransfers", [])

    if token_transfers:
        print("\nToken transfers:")

        for transfer in token_transfers:
            print(
                f"  {transfer.get('fromUserAccount')} -> "
                f"{transfer.get('toUserAccount')} | "
                f"mint={transfer.get('mint')} | "
                f"amount={transfer.get('tokenAmount')}"
            )

    if native_transfers:
        print("\nSOL transfers:")

        for transfer in native_transfers:
            print(
                f"  {transfer.get('fromUserAccount')} -> "
                f"{transfer.get('toUserAccount')} | "
                f"lamports={transfer.get('amount')}"
            )

    print("=" * 80)