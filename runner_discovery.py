import requests
from datetime import datetime, timezone


DEXSCREENER_URL = "https://api.dexscreener.com/token-profiles/latest/v1"


def fetch_latest_tokens():
    response = requests.get(
        DEXSCREENER_URL,
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
    url = f"https://api.dexscreener.com/token-pairs/v1/solana/{mint_address}"

    response = requests.get(
        url,
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def select_main_pair(pairs):
    if not pairs:
        return None

    usable_pairs = [
        pair
        for pair in pairs
        if pair.get("liquidity", {}).get("usd", 0) > 0
    ]

    if not usable_pairs:
        return None

    return max(
        usable_pairs,
        key=lambda pair: pair.get("liquidity", {}).get("usd", 0),
    )


def analyze_token(token):
    mint = token["tokenAddress"]

    pairs = fetch_token_pairs(mint)

    main_pair = select_main_pair(pairs)

    if not main_pair:
        return None

    price_change = main_pair.get("priceChange", {})
    volume = main_pair.get("volume", {})
    txns = main_pair.get("txns", {})
    liquidity = main_pair.get("liquidity", {})

    pair_created_at = main_pair.get("pairCreatedAt")

    if pair_created_at:
        pair_created = datetime.fromtimestamp(
            pair_created_at / 1000,
            tz=timezone.utc,
        ).isoformat()
    else:
        pair_created = None

    return {
        "mint": mint,
        "name": main_pair.get("baseToken", {}).get("name"),
        "symbol": main_pair.get("baseToken", {}).get("symbol"),
        "dex": main_pair.get("dexId"),
        "pair_address": main_pair.get("pairAddress"),
        "price_usd": main_pair.get("priceUsd"),
        "market_cap": main_pair.get("marketCap"),
        "fdv": main_pair.get("fdv"),
        "liquidity_usd": liquidity.get("usd"),
        "volume_5m": volume.get("m5"),
        "volume_1h": volume.get("h1"),
        "volume_24h": volume.get("h24"),
        "price_change_5m": price_change.get("m5"),
        "price_change_1h": price_change.get("h1"),
        "price_change_24h": price_change.get("h24"),
        "buys_5m": txns.get("m5", {}).get("buys"),
        "sells_5m": txns.get("m5", {}).get("sells"),
        "buys_1h": txns.get("h1", {}).get("buys"),
        "sells_1h": txns.get("h1", {}).get("sells"),
        "pair_created_at": pair_created,
    }


def main():
    tokens = fetch_latest_tokens()

    print(f"Solana tokens discovered: {len(tokens)}")
    print()

    for token in tokens[:10]:
        try:
            result = analyze_token(token)

            if not result:
                continue

            print(
                f"{result['symbol']:<12} "
                f"MC=${result['market_cap']} "
                f"Liquidity=${result['liquidity_usd']} "
                f"Vol1h=${result['volume_1h']} "
                f"1h={result['price_change_1h']}% "
                f"Buys/Sells={result['buys_1h']}/{result['sells_1h']} "
                f"DEX={result['dex']}"
            )

        except Exception as error:
            print(
                f"ERROR {token.get('tokenAddress')}: {error}"
            )


if __name__ == "__main__":
    main()