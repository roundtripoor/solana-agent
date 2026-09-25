import os
import re
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from supabase import create_client

from token_registry import get_or_create_token


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing")

if not SUPABASE_SECRET_KEY:
    raise ValueError("SUPABASE_SECRET_KEY is missing")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


# ============================================================
# LOAD SWAP TRANSACTIONS
# ============================================================

def get_swap_transactions(limit=1000):

    response = (
        supabase
        .table("raw_transactions")
        .select("*")
        .eq("transaction_type", "SWAP")
        .order("block_time", desc=False)
        .limit(limit)
        .execute()
    )

    return response.data


# ============================================================
# PARSE HELIUS SWAP DESCRIPTION
# ============================================================

def parse_swap_description(description):

    if not description:
        return None

    pattern = re.compile(
        r"swapped\s+"
        r"([0-9.,]+)\s+(.+?)\s+"
        r"for\s+"
        r"([0-9.,]+)\s+(.+)$",
        re.IGNORECASE,
    )

    match = pattern.search(description)

    if not match:
        return None

    try:

        input_amount = Decimal(
            match.group(1).replace(",", "")
        )

        output_amount = Decimal(
            match.group(3).replace(",", "")
        )

    except InvalidOperation:

        return None

    return {
        "input_amount": input_amount,
        "input_asset": match.group(2).strip(),
        "output_amount": output_amount,
        "output_asset": match.group(4).strip(),
    }


# ============================================================
# FIND WALLET TOKEN MOVEMENTS
# ============================================================

def find_wallet_token_movements(raw, wallet):

    movements = []

    for transfer in raw.get("tokenTransfers", []):

        sender = transfer.get("fromUserAccount")
        receiver = transfer.get("toUserAccount")

        if sender != wallet and receiver != wallet:
            continue

        amount = transfer.get("tokenAmount")

        if amount is None:
            continue

        try:

            amount = Decimal(str(amount))

        except InvalidOperation:

            continue

        movements.append(
            {
                "mint": transfer.get("mint"),
                "amount": amount,
                "direction": (
                    "OUT"
                    if sender == wallet
                    else "IN"
                ),
            }
        )

    return movements


# ============================================================
# FIND MATCHING MOVEMENT
# ============================================================

def find_matching_movement(
    movements,
    amount,
    direction,
):

    candidates = [
        movement
        for movement in movements
        if movement["direction"] == direction
    ]

    if not candidates:
        return None

    best = None
    best_difference = None

    for movement in candidates:

        difference = abs(
            movement["amount"] - amount
        )

        if (
            best_difference is None
            or difference < best_difference
        ):

            best = movement
            best_difference = difference

    if best is None or amount == 0:
        return None

    relative_difference = (
        best_difference / abs(amount)
    )

    if relative_difference <= Decimal("0.01"):
        return best

    return None


# ============================================================
# REGISTER TOKEN
# ============================================================

def register_token(mint):

    token = get_or_create_token(mint)

    return {
        "mint": mint,
        "name": token.get("name"),
        "symbol": token.get("symbol"),
    }


# ============================================================
# BUILD NORMALIZED SWAP LEGS
# ============================================================

def build_swap_legs(tx):

    raw = tx["raw_data"]
    wallet = tx["wallet_address"]

    parsed = parse_swap_description(
        tx.get("description")
    )

    if not parsed:
        return None

    movements = find_wallet_token_movements(
        raw,
        wallet,
    )

    input_match = find_matching_movement(
        movements,
        parsed["input_amount"],
        "OUT",
    )

    output_match = find_matching_movement(
        movements,
        parsed["output_amount"],
        "IN",
    )

    if not input_match or not output_match:
        return None

    input_mint = input_match["mint"]
    output_mint = output_match["mint"]

    if not input_mint or not output_mint:
        return None

    input_token = register_token(input_mint)
    output_token = register_token(output_mint)

    input_amount = parsed["input_amount"]
    output_amount = parsed["output_amount"]

    source = raw.get("source")

    common = {
        "signature": tx["signature"],
        "slot": tx.get("slot"),
        "block_time": tx.get("block_time"),
        "wallet_address": wallet,
        "pool_address": None,
        "source": source,
        "classification_confidence": 1.0,
        "classification_method": (
            "helius_description_transfer_match"
        ),
        "raw_transaction_id": tx["id"],
        "metadata": {
            "description_input_asset": parsed[
                "input_asset"
            ],
            "description_output_asset": parsed[
                "output_asset"
            ],
        },
    }

    # ========================================================
    # SELL LEG
    # ========================================================

    sell_leg = {
        **common,
        "event_index": 0,
        "token_mint": input_mint,
        "token_symbol": input_token["symbol"],
        "token_name": input_token["name"],
        "side": "SELL",
        "token_amount": str(input_amount),
        "quote_mint": output_mint,
        "quote_amount": str(output_amount),
        "quote_symbol": output_token["symbol"],
    }

    # ========================================================
    # BUY LEG
    # ========================================================

    buy_leg = {
        **common,
        "event_index": 1,
        "token_mint": output_mint,
        "token_symbol": output_token["symbol"],
        "token_name": output_token["name"],
        "side": "BUY",
        "token_amount": str(output_amount),
        "quote_mint": input_mint,
        "quote_amount": str(input_amount),
        "quote_symbol": input_token["symbol"],
    }

    return sell_leg, buy_leg


# ============================================================
# STORE NORMALIZED SWAP
# ============================================================

def store_swap(tx):

    legs = build_swap_legs(tx)

    if not legs:
        return False

    sell_leg, buy_leg = legs

    response = (
        supabase
        .table("token_swaps")
        .upsert(
            [sell_leg, buy_leg],
            on_conflict="signature,event_index",
        )
        .execute()
    )

    return bool(response.data)


# ============================================================
# MAIN
# ============================================================

def main():

    transactions = get_swap_transactions()

    print(
        f"SWAP transactions found: "
        f"{len(transactions)}"
    )

    stored = 0
    skipped = 0

    for index, tx in enumerate(
        transactions,
        start=1,
    ):

        try:

            success = store_swap(tx)

            if success:

                stored += 1

                print(
                    f"[{index}/{len(transactions)}] "
                    f"STORED "
                    f"{tx['signature']}"
                )

            else:

                skipped += 1

                print(
                    f"[{index}/{len(transactions)}] "
                    f"SKIPPED "
                    f"{tx['signature']}"
                )

        except Exception as error:

            skipped += 1

            print(
                f"[{index}/{len(transactions)}] "
                f"ERROR "
                f"{tx['signature']}: "
                f"{error}"
            )

    print()
    print("========================================")
    print("SWAP NORMALIZATION COMPLETE")
    print(f"Transactions stored: {stored}")
    print(f"Transactions skipped: {skipped}")
    print("========================================")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()