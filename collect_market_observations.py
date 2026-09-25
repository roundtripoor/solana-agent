import os
import requests
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is missing from .env")

if not SUPABASE_SECRET_KEY:
    raise ValueError("SUPABASE_SECRET_KEY is missing from .env")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


DEXSCREENER_PROFILES_URL = (
    "https://api.dexscreener.com/token-profiles/latest/v1"
)


def fetch_latest_tokens():
    response = requests.get(
        DEXSCREENER_PROFILES_URL,
        timeout=15,
    )

    response.raise_for_status()

    tokens = response.json()

    return [
        token
        for token in tokens
        if token.get("chainId") == "solana"
    ]


def fetch_token_pairs(mint_address):
    url = (
        f"https://api.dexscreener.com/"
        f"token-pairs/v1/solana/{mint_address}"
    )

    response = requests.get(
        url,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def parse_pair(pair):
    price_change = pair.get("priceChange", {})
    volume = pair.get("volume", {})
    txns = pair.get("txns", {})
    liquidity = pair.get("liquidity", {})
    base_token = pair.get("baseToken", {})

    pair_created_at = pair.get("pairCreatedAt")

    if pair_created_at:
        pair_created = datetime.fromtimestamp(
            pair_created_at / 1000,
            tz=timezone.utc,
        ).isoformat()
    else:
        pair_created = None

    return {
        "token_mint": base_token.get("address"),
        "token_symbol": base_token.get("symbol"),
        "token_name": base_token.get("name"),

        "observed_at": datetime.now(timezone.utc).isoformat(),

        "dex": pair.get("dexId"),
        "pair_address": pair.get("pairAddress"),

        "price_usd": pair.get("priceUsd"),
        "market_cap": pair.get("marketCap"),
        "fdv": pair.get("fdv"),
        "liquidity_usd": liquidity.get("usd"),

        "volume_5m_usd": volume.get("m5"),
        "volume_1h_usd": volume.get("h1"),
        "volume_24h_usd": volume.get("h24"),

        "price_change_5m": price_change.get("m5"),
        "price_change_1h": price_change.get("h1"),
        "price_change_24h": price_change.get("h24"),

        "buys_5m": txns.get("m5", {}).get("buys"),
        "sells_5m": txns.get("m5", {}).get("sells"),

        "buys_1h": txns.get("h1", {}).get("buys"),
        "sells_1h": txns.get("h1", {}).get("sells"),

        "pair_created_at": pair_created,

        "raw_data": pair,
    }


def store_observation(observation):
    supabase.table("market_observations").insert(
        observation
    ).execute()


def main():
    print("=" * 40)
    print("MARKET OBSERVATION COLLECTOR")
    print("=" * 40)

    tokens = fetch_latest_tokens()

    print(
        f"Solana candidate tokens discovered: {len(tokens)}"
    )
    print()

    stored = 0
    skipped = 0
    errors = 0

    for index, token in enumerate(tokens, start=1):
        mint = token.get("tokenAddress")

        if not mint:
            skipped += 1
            continue

        try:
            pairs = fetch_token_pairs(mint)

            if not pairs:
                skipped += 1
                continue

            usable_pairs = [
                pair
                for pair in pairs
                if pair.get("liquidity", {}).get("usd", 0) > 0
            ]

            if not usable_pairs:
                skipped += 1
                continue

            for pair in usable_pairs:
                observation = parse_pair(pair)

                if not observation["token_mint"]:
                    continue

                store_observation(observation)

                stored += 1

            print(
                f"[{index}/{len(tokens)}] "
                f"{token.get('tokenAddress')} "
                f"→ stored {len(usable_pairs)} pair(s)"
            )

        except Exception as error:
            errors += 1

            print(
                f"[{index}/{len(tokens)}] "
                f"ERROR {mint}: {error}"
            )

    print()
    print("=" * 40)
    print("COLLECTION COMPLETE")
    print("=" * 40)
    print(f"Observations stored: {stored}")
    print(f"Tokens skipped:      {skipped}")
    print(f"Errors:              {errors}")
    print("=" * 40)


if __name__ == "__main__":
    main()