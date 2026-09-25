import os
import requests
from dotenv import load_dotenv


load_dotenv()

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")

if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY is missing")


HELIUS_RPC_URL = (
    f"https://mainnet.helius-rpc.com/"
    f"?api-key={HELIUS_API_KEY}"
)


def get_token_metadata(mint_address):
    response = requests.post(
        HELIUS_RPC_URL,
        json={
            "jsonrpc": "2.0",
            "id": "token-metadata",
            "method": "getAsset",
            "params": {
                "id": mint_address,
                "displayOptions": {
                    "showFungible": True
                }
            },
        },
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:
        return {
            "mint": mint_address,
            "name": None,
            "symbol": None,
        }

    asset = data.get("result", {})

    metadata = (
        asset
        .get("content", {})
        .get("metadata", {})
    )

    return {
        "mint": mint_address,
        "name": metadata.get("name"),
        "symbol": metadata.get("symbol"),
    }


def main():
    # Test token: USDC
    mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    result = get_token_metadata(mint)

    print("Token metadata:")
    print(f"Mint:   {result['mint']}")
    print(f"Name:   {result['name']}")
    print(f"Symbol: {result['symbol']}")


if __name__ == "__main__":
    main()