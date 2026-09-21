import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HELIUS_API_KEY")

if not api_key:
    raise Exception("HELIUS_API_KEY not found")

url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"

response = requests.post(
    url,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getLatestBlockhash",
        "params": [{"commitment": "confirmed"}],
    },
)

print(response.json())
