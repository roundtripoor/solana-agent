import os
from collections import Counter
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client


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
# SETTINGS
# ============================================================

WALLET = "8V4kM8JEGa4godgzbvAksQUtMNJ9GyPCxKqS6vUFTf72"


# ============================================================
# LOAD WALLET SWAPS
# ============================================================

def get_wallet_swaps():

    response = (
        supabase
        .table("token_swaps")
        .select("*")
        .eq("wallet_address", WALLET)
        .order("block_time", desc=False)
        .execute()
    )

    return response.data


# ============================================================
# FORMAT TIMESTAMP
# ============================================================

def format_timestamp(block_time):

    if not block_time:
        return "Unknown"

    return datetime.fromtimestamp(
        block_time,
        tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S UTC")


# ============================================================
# MAIN ANALYSIS
# ============================================================

def main():

    swaps = get_wallet_swaps()

    print()
    print("========================================")
    print("WALLET BEHAVIOR REPORT")
    print("========================================")
    print()
    print(f"Wallet: {WALLET}")
    print()

    if not swaps:

        print("No normalized swaps found.")
        return


    # ========================================================
    # BASIC COUNTS
    # ========================================================

    buy_rows = [
        row
        for row in swaps
        if row.get("side") == "BUY"
    ]

    sell_rows = [
        row
        for row in swaps
        if row.get("side") == "SELL"
    ]

    unique_tokens = set(
        row.get("token_mint")
        for row in swaps
        if row.get("token_mint")
    )

    unique_symbols = set(
        row.get("token_symbol")
        for row in swaps
        if row.get("token_symbol")
    )


    print("BASIC ACTIVITY")
    print("----------------------------------------")
    print(f"Normalized swap legs: {len(swaps)}")
    print(f"BUY legs:              {len(buy_rows)}")
    print(f"SELL legs:             {len(sell_rows)}")
    print(f"Unique tokens:         {len(unique_tokens)}")
    print()


    # ========================================================
    # TIME RANGE
    # ========================================================

    block_times = [
        row.get("block_time")
        for row in swaps
        if row.get("block_time")
    ]

    if block_times:

        earliest = min(block_times)
        latest = max(block_times)

        print("OBSERVED TIME RANGE")
        print("----------------------------------------")
        print(f"Earliest: {format_timestamp(earliest)}")
        print(f"Latest:   {format_timestamp(latest)}")
        print()


    # ========================================================
    # MOST TRADED TOKENS
    # ========================================================

    token_counter = Counter()

    for row in swaps:

        symbol = row.get("token_symbol")
        mint = row.get("token_mint")

        display_name = symbol or mint

        token_counter[display_name] += 1


    print("MOST TRADED TOKENS")
    print("----------------------------------------")

    for token, count in token_counter.most_common(15):

        print(
            f"{token:<15} "
            f"{count} legs"
        )

    print()


    # ========================================================
    # BUY TOKENS
    # ========================================================

    buy_counter = Counter()

    for row in buy_rows:

        symbol = row.get("token_symbol")
        mint = row.get("token_mint")

        display_name = symbol or mint

        buy_counter[display_name] += 1


    print("MOST FREQUENTLY BOUGHT")
    print("----------------------------------------")

    for token, count in buy_counter.most_common(15):

        print(
            f"{token:<15} "
            f"{count} BUYs"
        )

    print()


    # ========================================================
    # SELL TOKENS
    # ========================================================

    sell_counter = Counter()

    for row in sell_rows:

        symbol = row.get("token_symbol")
        mint = row.get("token_mint")

        display_name = symbol or mint

        sell_counter[display_name] += 1


    print("MOST FREQUENTLY SOLD")
    print("----------------------------------------")

    for token, count in sell_counter.most_common(15):

        print(
            f"{token:<15} "
            f"{count} SELLs"
        )

    print()


    # ========================================================
    # QUOTE ASSETS
    # ========================================================

    quote_counter = Counter()

    for row in swaps:

        quote_symbol = row.get("quote_symbol")

        if quote_symbol:

            quote_counter[quote_symbol] += 1


    print("QUOTE ASSETS")
    print("----------------------------------------")

    for asset, count in quote_counter.most_common():

        print(
            f"{asset:<15} "
            f"{count} times"
        )

    print()


    # ========================================================
    # ACTIVITY BY DAY
    # ========================================================

    daily_counter = Counter()

    for row in swaps:

        block_time = row.get("block_time")

        if not block_time:
            continue

        date = datetime.fromtimestamp(
            block_time,
            tz=timezone.utc,
        ).strftime("%Y-%m-%d")

        daily_counter[date] += 1


    print("ACTIVITY BY DAY")
    print("----------------------------------------")

    for date, count in sorted(
        daily_counter.items()
    ):

        print(
            f"{date}: "
            f"{count} swap legs"
        )

    print()


    # ========================================================
    # BUY / SELL TOKEN OVERLAP
    # ========================================================

    bought_mints = set(
        row.get("token_mint")
        for row in buy_rows
        if row.get("token_mint")
    )

    sold_mints = set(
        row.get("token_mint")
        for row in sell_rows
        if row.get("token_mint")
    )

    bought_and_sold = (
        bought_mints & sold_mints
    )

    bought_only = (
        bought_mints - sold_mints
    )

    sold_only = (
        sold_mints - bought_mints
    )


    print("TOKEN OVERLAP")
    print("----------------------------------------")
    print(
        f"Bought AND sold: "
        f"{len(bought_and_sold)}"
    )

    print(
        f"Bought but not sold "
        f"in observed history: "
        f"{len(bought_only)}"
    )

    print(
        f"Sold but not bought "
        f"in observed history: "
        f"{len(sold_only)}"
    )

    print()


    # ========================================================
    # DISCLAIMER ABOUT OBSERVATION WINDOW
    # ========================================================

    print("IMPORTANT")
    print("----------------------------------------")
    print(
        "This report describes only the "
        "transactions currently present in "
        "our database."
    )

    print(
        "It does NOT calculate profitability, "
        "wallet quality, or predictive power."
    )

    print(
        "A token appearing as BUY-only or "
        "SELL-only may simply fall outside "
        "the current observation window."
    )

    print()

    print("========================================")
    print("END WALLET REPORT")
    print("========================================")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()