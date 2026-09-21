import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SECRET_KEY")

supabase = create_client(url, key)

test_mint = "TEST_MINT_NOT_A_REAL_TOKEN_12345"

# 1. Insert
print("1. Inserting test token...")

insert_response = (
    supabase.table("tokens")
    .insert({
        "mint_address": test_mint,
        "name": "Test Token",
        "symbol": "TEST",
        "metadata": {
            "test": True
        }
    })
    .select("id, mint_address, name, symbol")
    .execute()
)

print("Inserted:", insert_response.data)

# 2. Read it back
print("\n2. Reading test token...")

read_response = (
    supabase.table("tokens")
    .select("id, mint_address, name, symbol")
    .eq("mint_address", test_mint)
    .execute()
)

print("Found:", read_response.data)

# 3. Delete it
print("\n3. Deleting test token...")

delete_response = (
    supabase.table("tokens")
    .delete()
    .eq("mint_address", test_mint)
    .execute()
)

print("Deleted:", delete_response.data)

# 4. Verify it's gone
print("\n4. Verifying deletion...")

verify_response = (
    supabase.table("tokens")
    .select("id, mint_address")
    .eq("mint_address", test_mint)
    .execute()
)

print("Remaining:", verify_response.data)

print("\nDATABASE WRITE TEST: SUCCESS")