import os

from dotenv import load_dotenv
from supabase import create_client

from token_metadata import get_token_metadata


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


def get_or_create_token(mint_address):
    """
    Return token metadata from Supabase.

    If the token isn't already registered,
    fetch its metadata from Helius and store it.
    """

    existing = (
        supabase
        .table("tokens")
        .select("*")
        .eq("mint_address", mint_address)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]

    metadata = get_token_metadata(mint_address)

    row = {
        "mint_address": mint_address,
        "name": metadata.get("name"),
        "symbol": metadata.get("symbol"),
        "metadata": {
            "source": "helius_getAsset"
        },
    }

    inserted = (
        supabase
        .table("tokens")
        .insert(row)
        .execute()
    )

    if not inserted.data:
        raise RuntimeError(
            f"Failed to register token {mint_address}"
        )

    return inserted.data[0]


def main():
    # Test with USDC
    mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    token = get_or_create_token(mint)

    print("Token registered:")
    print(f"Mint:   {token['mint_address']}")
    print(f"Name:   {token['name']}")
    print(f"Symbol: {token['symbol']}")


if __name__ == "__main__":
    main()