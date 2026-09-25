import os
import sys
import json
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not HELIUS_API_KEY:
    raise RuntimeError("Missing HELIUS_API_KEY in .env")

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL in .env")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY in .env")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
)


def fetch_token_transactions(token_mint, limit=100):
    url = (
        f"https://api.helius.xyz/v0/addresses/"
        f"{token_mint}/transactions"
    )

    params = {
        "api-key": HELIUS_API_KEY,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json()


def summarize_transaction(tx):
    """
    Create a compact evidence record.

    IMPORTANT:
    This does NOT decide whether a wallet is a sniper,
    bundler, farmer, insider, etc.

    We preserve observations and let later analysis
    determine what they mean.
    """

    return {
        "signature": tx.get("signature"),
        "slot": tx.get("slot"),
        "timestamp": tx.get("timestamp"),
        "type": tx.get("type"),
        "source": tx.get("source"),
        "description": tx.get("description"),
        "fee_payer": tx.get("feePayer"),
        "fee": tx.get("fee"),
        "transaction_error": tx.get("transactionError"),
        "native_transfers": tx.get("nativeTransfers", []),
        "token_transfers": tx.get("tokenTransfers", []),
        "account_data": tx.get("accountData", []),
        "instructions": tx.get("instructions", []),
    }


def build_early_wallet_observations(transactions):
    """
    Extract wallets appearing in the earliest observed
    transactions.

    This is deliberately descriptive.
    No wallet quality score is created here.
    """

    wallets = {}

    for tx_index, tx in enumerate(transactions):
        timestamp = tx.get("timestamp")
        fee_payer = tx.get("feePayer")

        participants = set()

        if fee_payer:
            participants.add(fee_payer)

        for transfer in tx.get("nativeTransfers", []):
            sender = transfer.get("fromUserAccount")
            receiver = transfer.get("toUserAccount")

            if sender:
                participants.add(sender)

            if receiver:
                participants.add(receiver)

        for transfer in tx.get("tokenTransfers", []):
            sender = transfer.get("fromUserAccount")
            receiver = transfer.get("toUserAccount")

            if sender:
                participants.add(sender)

            if receiver:
                participants.add(receiver)

        for wallet in participants:
            if wallet not in wallets:
                wallets[wallet] = {
                    "wallet": wallet,
                    "first_tx_index": tx_index,
                    "first_timestamp": timestamp,
                    "transaction_count": 0,
                }

            wallets[wallet]["transaction_count"] += 1

    return sorted(
        wallets.values(),
        key=lambda x: (
            x["first_timestamp"] or 0,
            x["first_tx_index"],
        ),
    )


def unix_to_iso(timestamp):
    if not timestamp:
        return None

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def save_analysis(
    token_mint,
    transactions,
    wallet_observations,
):
    timestamps = [
        tx.get("timestamp")
        for tx in transactions
        if tx.get("timestamp")
    ]

    timestamps.sort()

    first_seen_at = unix_to_iso(timestamps[0]) if timestamps else None
    launch_time = first_seen_at

    first_1m_wallets = wallet_observations[:100]
    first_5m_wallets = wallet_observations[:500]
    first_15m_wallets = wallet_observations[:1000]

    raw_evidence = {
        "collection_method": "helius_address_transactions",
        "transaction_count": len(transactions),
        "transactions": transactions,
        "wallet_observations": wallet_observations,
    }

    row = {
        "token_mint": token_mint,
        "first_seen_at": first_seen_at,
        "launch_time": launch_time,
        "creator_address": None,
        "launchpad": None,
        "first_1m_wallets": first_1m_wallets,
        "first_5m_wallets": first_5m_wallets,
        "first_15m_wallets": first_15m_wallets,
        "funding_relationships": [],
        "early_transactions": [
            summarize_transaction(tx)
            for tx in transactions
        ],
        "raw_evidence": raw_evidence,
        "analysis_status": "RAW",
    }

    result = (
        supabase
        .table("token_launch_analysis")
        .upsert(
            row,
            on_conflict="token_mint",
        )
        .execute()
    )

    return result


def main():
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python launch_forensics.py <TOKEN_MINT>"
        )
        sys.exit(1)

    token_mint = sys.argv[1]

    print()
    print("========================================")
    print("LAUNCH FORENSICS")
    print("========================================")
    print(f"Token: {token_mint}")
    print()

    print("Fetching Helius transaction history...")

    transactions = fetch_token_transactions(
        token_mint,
        limit=100,
    )

    print(f"Transactions fetched: {len(transactions)}")

    if not transactions:
        print("No transactions returned.")
        return

    # Helius normally returns newest first.
    # Reverse so earliest activity comes first.
    transactions = sorted(
        transactions,
        key=lambda tx: tx.get("timestamp") or 0,
    )

    print(
        "Earliest timestamp:",
        unix_to_iso(transactions[0].get("timestamp")),
    )

    print(
        "Latest timestamp:",
        unix_to_iso(transactions[-1].get("timestamp")),
    )

    wallet_observations = build_early_wallet_observations(
        transactions
    )

    print(
        "Unique observed wallets:",
        len(wallet_observations),
    )

    print()
    print("EARLIEST OBSERVED WALLETS")

    for wallet in wallet_observations[:20]:
        print(
            f"{wallet['wallet']} | "
            f"tx_index={wallet['first_tx_index']} | "
            f"timestamp={unix_to_iso(wallet['first_timestamp'])}"
        )

    print()
    print("Saving RAW evidence to Supabase...")

    save_analysis(
        token_mint,
        transactions,
        wallet_observations,
    )

    print("Saved.")
    print()
    print("Status: RAW")
    print(
        "No wallet scores, farm labels, bundle labels, "
        "or conclusions were generated."
    )


if __name__ == "__main__":
    main()
    