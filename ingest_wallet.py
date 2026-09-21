import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY is missing")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing")

if not SUPABASE_SECRET_KEY:
    raise ValueError("SUPABASE_SECRET_KEY is missing")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)

WALLET = "8V4kM8JEGa4godgzbvAksQUtMNJ9GyPCxKqS6vUFTf72"

BASE_URL = f"https://api.helius.xyz/v0/addresses/{WALLET}/transactions"

MAX_PAGES = 5
LIMIT = 20

before = None
total_fetched = 0
total_stored = 0

for page in range(1, MAX_PAGES + 1):

    params = {
        "api-key": HELIUS_API_KEY,
        "limit": LIMIT,
    }

    if before:
        params["before"] = before

    print(f"\nFetching page {page}/{MAX_PAGES}...")

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Helius error {response.status_code}: {response.text}"
        )

    transactions = response.json()

    if not transactions:
        print("No more transactions available.")
        break

    rows = []

    for tx in transactions:
        signature = tx.get("signature")

        if not signature:
            continue

        rows.append({
            "signature": signature,
            "wallet_address": WALLET,
            "slot": tx.get("slot"),
            "block_time": tx.get("timestamp"),
            "transaction_type": tx.get("type"),
            "description": tx.get("description"),
            "raw_data": tx,
        })

    if rows:
        result = (
            supabase
            .table("raw_transactions")
            .upsert(
                rows,
                on_conflict="signature",
            )
            .execute()
        )

        stored = len(result.data)
    else:
        stored = 0

    total_fetched += len(transactions)
    total_stored += stored

    oldest_signature = transactions[-1].get("signature")

    print(f"Fetched: {len(transactions)}")
    print(f"Stored/upserted: {stored}")
    print(f"Total fetched: {total_fetched}")

    if not oldest_signature:
        break

    before = oldest_signature

print("\n" + "=" * 50)
print("HISTORICAL INGESTION TEST COMPLETE")
print("=" * 50)
print(f"Transactions fetched: {total_fetched}")
print(f"Transactions stored/upserted: {total_stored}")