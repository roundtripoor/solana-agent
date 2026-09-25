import os
import requests

from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# ENVIRONMENT
# ============================================================

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


# ============================================================
# CONNECTIONS
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


# ============================================================
# SETTINGS
# ============================================================

# Wallet we are currently studying.
WALLET = "8V4kM8JEGa4godgzbvAksQUtMNJ9GyPCxKqS6vUFTf72"

# Maximum number of transactions to collect
# during this run.
MAX_TRANSACTIONS = 1000

# Helius allows up to 100 transactions per request.
PAGE_SIZE = 100


# ============================================================
# FETCH ONE PAGE FROM HELIUS
# ============================================================

def fetch_transactions(wallet, before=None):

    url = (
        f"https://api.helius.xyz/v0/addresses/"
        f"{wallet}/transactions"
    )

    params = {
        "api-key": HELIUS_API_KEY,
        "limit": PAGE_SIZE,
    }

    if before:
        params["before"] = before

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Helius error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return response.json()


# ============================================================
# STORE TRANSACTIONS
# ============================================================

def store_transactions(transactions, wallet):

    if not transactions:
        return 0

    rows = []

    for tx in transactions:

        signature = tx.get("signature")

        if not signature:
            continue

        rows.append(
            {
                "signature": signature,
                "wallet_address": wallet,
                "slot": tx.get("slot"),
                "block_time": tx.get("timestamp"),
                "transaction_type": tx.get("type"),
                "description": tx.get("description"),
                "raw_data": tx,
            }
        )

    if not rows:
        return 0

    response = (
        supabase
        .table("raw_transactions")
        .upsert(
            rows,
            on_conflict="signature",
        )
        .execute()
    )

    return len(response.data)


# ============================================================
# MAIN BACKFILL
# ============================================================

def main():

    print("========================================")
    print("SOLANA WALLET HISTORICAL BACKFILL")
    print("========================================")
    print()
    print(f"Wallet: {WALLET}")
    print(f"Target: {MAX_TRANSACTIONS} transactions")
    print()

    total_fetched = 0
    total_stored = 0

    before = None
    page_number = 0

    while total_fetched < MAX_TRANSACTIONS:

        page_number += 1

        print(
            f"Fetching page "
            f"{page_number}..."
        )

        transactions = fetch_transactions(
            WALLET,
            before,
        )

        if not transactions:

            print(
                "Helius returned no more "
                "transactions."
            )

            break

        # Don't exceed our requested target.
        remaining = (
            MAX_TRANSACTIONS
            - total_fetched
        )

        transactions = transactions[:remaining]

        fetched_count = len(transactions)

        print(
            f"Fetched: {fetched_count}"
        )

        stored_count = store_transactions(
            transactions,
            WALLET,
        )

        print(
            f"Stored/upserted: "
            f"{stored_count}"
        )

        total_fetched += fetched_count
        total_stored += stored_count

        print(
            f"Total fetched: "
            f"{total_fetched}"
        )

        print()

        # The last transaction in the page is
        # the oldest transaction in this batch.
        #
        # We use its signature to request the
        # next older page.
        oldest_signature = transactions[-1].get(
            "signature"
        )

        if not oldest_signature:

            print(
                "Could not find oldest "
                "transaction signature."
            )

            break

        before = oldest_signature

        # If Helius returned fewer than the
        # requested page size, we've reached
        # the end of the available history.
        if fetched_count < PAGE_SIZE:

            print(
                "Reached the end of the "
                "available transaction history."
            )

            break

    print()
    print("========================================")
    print("HISTORICAL BACKFILL COMPLETE")
    print(
        f"Transactions fetched: "
        f"{total_fetched}"
    )
    print(
        f"Transactions stored/upserted: "
        f"{total_stored}"
    )
    print(
        f"Pages processed: "
        f"{page_number}"
    )
    print("========================================")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()