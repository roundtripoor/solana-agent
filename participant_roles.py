import json
import sys
from collections import defaultdict


# ------------------------------------------------------------
# Usage
# ------------------------------------------------------------
if len(sys.argv) < 2:
    raise ValueError(
        "Usage: python participant_roles.py <RAW_TRANSACTION_JSON> [TOKEN_MINT]"
    )

INPUT_FILE = sys.argv[1]
TARGET_MINT = sys.argv[2] if len(sys.argv) >= 3 else None


# ------------------------------------------------------------
# Known infrastructure / program IDs
# ------------------------------------------------------------
KNOWN_PROGRAMS = {
    # System Program
    "11111111111111111111111111111111",

    # Token Program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",

    # Token-2022
    "TokenzQdBNbLqP5VEh6sYJ9dW9V9fLx1qJ9Q7nYxQ",

    # Associated Token Program
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efT8",

    # Compute Budget
    "ComputeBudget111111111111111111111111111111",

    # Memo
    "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",

    # Sysvar examples
    "Sysvar1111111111111111111111111111111111111",
    "SysvarC1ock11111111111111111111111111111111",
    "SysvarRent111111111111111111111111111111111",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def add_evidence(role_map, address, role, evidence):
    if not address:
        return

    if address not in role_map:
        role_map[address] = {
            "address": address,
            "roles": [],
            "evidence": [],
        }

    if role not in role_map[address]["roles"]:
        role_map[address]["roles"].append(role)

    if evidence not in role_map[address]["evidence"]:
        role_map[address]["evidence"].append(evidence)


def add_many(role_map, addresses, role, evidence):
    for address in addresses:
        add_evidence(role_map, address, role, evidence)


def safe_list(value):
    return value if isinstance(value, list) else []


def get_address(obj):
    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        return (
            obj.get("address")
            or obj.get("account")
            or obj.get("pubkey")
            or obj.get("owner")
        )

    return None


# ------------------------------------------------------------
# Load transaction
# ------------------------------------------------------------
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    tx = json.load(f)


# ------------------------------------------------------------
# Basic transaction information
# ------------------------------------------------------------
signature = tx.get("signature")
slot = tx.get("slot")
timestamp = tx.get("timestamp")
tx_type = tx.get("type")
source = tx.get("source")
fee_payer = tx.get("feePayer")
description = tx.get("description")


# ------------------------------------------------------------
# Role map
# ------------------------------------------------------------
roles = {}


# ------------------------------------------------------------
# Fee payer
# ------------------------------------------------------------
if fee_payer:
    add_evidence(
        roles,
        fee_payer,
        "fee_payer",
        "Helius feePayer",
    )


# ------------------------------------------------------------
# Native transfers
# ------------------------------------------------------------
native_transfers = safe_list(tx.get("nativeTransfers"))

for transfer in native_transfers:
    sender = transfer.get("fromUserAccount")
    receiver = transfer.get("toUserAccount")

    amount = transfer.get("amount")

    if sender:
        add_evidence(
            roles,
            sender,
            "native_sender",
            f"native transfer sender ({amount} lamports)",
        )

    if receiver:
        add_evidence(
            roles,
            receiver,
            "native_receiver",
            f"native transfer receiver ({amount} lamports)",
        )


# ------------------------------------------------------------
# Token transfers
# ------------------------------------------------------------
token_transfers = safe_list(tx.get("tokenTransfers"))

token_mints = set()
token_accounts = set()
token_users = set()

for transfer in token_transfers:
    mint = transfer.get("mint")

    from_user = transfer.get("fromUserAccount")
    to_user = transfer.get("toUserAccount")

    from_token_account = transfer.get("fromTokenAccount")
    to_token_account = transfer.get("toTokenAccount")

    token_amount = transfer.get("tokenAmount")
    token_symbol = transfer.get("symbol")

    if mint:
        token_mints.add(mint)

    if from_token_account:
        token_accounts.add(from_token_account)

    if to_token_account:
        token_accounts.add(to_token_account)

    if from_user:
        token_users.add(from_user)

    if to_user:
        token_users.add(to_user)

    if from_user:
        evidence = "Helius tokenTransfers.fromUserAccount"

        if mint:
            evidence += f"; mint={mint}"

        if token_symbol:
            evidence += f"; symbol={token_symbol}"

        if token_amount is not None:
            evidence += f"; amount={token_amount}"

        add_evidence(
            roles,
            from_user,
            "token_user_account",
            evidence,
        )

    if to_user:
        evidence = "Helius tokenTransfers.toUserAccount"

        if mint:
            evidence += f"; mint={mint}"

        if token_symbol:
            evidence += f"; symbol={token_symbol}"

        if token_amount is not None:
            evidence += f"; amount={token_amount}"

        add_evidence(
            roles,
            to_user,
            "token_user_account",
            evidence,
        )

    if from_token_account:
        add_evidence(
            roles,
            from_token_account,
            "token_account",
            "Helius tokenTransfers.fromTokenAccount",
        )

    if to_token_account:
        add_evidence(
            roles,
            to_token_account,
            "token_account",
            "Helius tokenTransfers.toTokenAccount",
        )

    if mint:
        add_evidence(
            roles,
            mint,
            "mint",
            "Helius tokenTransfers.mint",
        )


# ------------------------------------------------------------
# Account data
# ------------------------------------------------------------
account_data = safe_list(tx.get("accountData"))

account_data_accounts = set()

for account in account_data:
    address = account.get("account")

    if not address:
        continue

    account_data_accounts.add(address)

    # Native balance changes
    native_change = account.get("nativeBalanceChange")

    if native_change is not None and native_change != 0:
        add_evidence(
            roles,
            address,
            "balance_change_account",
            f"accountData.nativeBalanceChange={native_change}",
        )

    # Token balance changes
    token_balance_changes = safe_list(
        account.get("tokenBalanceChanges")
    )

    for change in token_balance_changes:
        mint = change.get("mint")
        token_account = change.get("tokenAccount")
        user_account = change.get("userAccount")
        raw_amount = change.get("rawTokenAmount")

        if mint:
            token_mints.add(mint)

            add_evidence(
                roles,
                mint,
                "mint",
                "accountData.tokenBalanceChanges.mint",
            )

        if token_account:
            token_accounts.add(token_account)

            add_evidence(
                roles,
                token_account,
                "token_account",
                "accountData.tokenBalanceChanges.tokenAccount",
            )

        if user_account:
            token_users.add(user_account)

            add_evidence(
                roles,
                user_account,
                "token_user_account",
                "accountData.tokenBalanceChanges.userAccount",
            )

        if user_account:
            evidence = "accountData.tokenBalanceChanges.userAccount"

            if mint:
                evidence += f"; mint={mint}"

            if raw_amount:
                evidence += f"; rawTokenAmount={raw_amount}"

            add_evidence(
                roles,
                user_account,
                "token_balance_owner",
                evidence,
            )


# ------------------------------------------------------------
# Instructions / programs
# ------------------------------------------------------------
instructions = safe_list(tx.get("instructions"))

program_ids = set()
instruction_accounts = set()

for instruction in instructions:
    program_id = instruction.get("programId")

    if program_id:
        program_ids.add(program_id)

        add_evidence(
            roles,
            program_id,
            "program_id",
            "instructions[].programId",
        )

    accounts = safe_list(instruction.get("accounts"))

    for account in accounts:
        address = get_address(account)

        if not address:
            continue

        instruction_accounts.add(address)

        add_evidence(
            roles,
            address,
            "instruction_account",
            f"instruction account for program {program_id}",
        )


# ------------------------------------------------------------
# Classify known programs
# ------------------------------------------------------------
for program_id in program_ids:
    if program_id in KNOWN_PROGRAMS:
        add_evidence(
            roles,
            program_id,
            "known_infrastructure_program",
            "recognized Solana infrastructure/program ID",
        )


# ------------------------------------------------------------
# Detect explicit protocol/program context
#
# IMPORTANT:
# We do NOT call arbitrary instruction accounts pools.
#
# A pool/protocol account is only surfaced when there is
# explicit evidence from the transaction structure.
# ------------------------------------------------------------
possible_protocol_accounts = set()

for instruction in instructions:
    program_id = instruction.get("programId")

    accounts = safe_list(instruction.get("accounts"))

    if not program_id or not accounts:
        continue

    # Accounts participating in a program instruction are preserved
    # as instruction accounts. We do NOT infer pool/protocol status.
    #
    # The only deterministic protocol-account signal available here
    # is an account that also appears as a token account AND is used
    # directly by a non-infrastructure program instruction.
    if program_id not in KNOWN_PROGRAMS:
        for account in accounts:
            address = get_address(account)

            if address and address in token_accounts:
                possible_protocol_accounts.add(address)

                add_evidence(
                    roles,
                    address,
                    "possible_protocol_account",
                    f"token account used by non-infrastructure program {program_id}",
                )


# ------------------------------------------------------------
# Unknown / other accounts
#
# These are accounts seen in the transaction but not deterministically
# categorized by the evidence above.
# ------------------------------------------------------------
all_seen_accounts = set(roles.keys())

for address in account_data_accounts:
    all_seen_accounts.add(address)

for address in instruction_accounts:
    all_seen_accounts.add(address)

for address in token_accounts:
    all_seen_accounts.add(address)

for address in token_users:
    all_seen_accounts.add(address)

for address in token_mints:
    all_seen_accounts.add(address)

for address in program_ids:
    all_seen_accounts.add(address)


for address in sorted(all_seen_accounts):
    if address not in roles:
        add_evidence(
            roles,
            address,
            "unknown_other",
            "account observed in transaction but not deterministically classified",
        )


# ------------------------------------------------------------
# Target mint filtering
# ------------------------------------------------------------
target_token_transfers = []

if TARGET_MINT:
    for transfer in token_transfers:
        if transfer.get("mint") == TARGET_MINT:
            target_token_transfers.append(transfer)


# ------------------------------------------------------------
# Build clean output
# ------------------------------------------------------------
role_list = []

for address, data in roles.items():
    role_list.append(
        {
            "address": address,
            "roles": sorted(data["roles"]),
            "evidence": data["evidence"],
        }
    )

role_list.sort(key=lambda x: x["address"])


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
role_counts = defaultdict(int)

for item in role_list:
    for role in item["roles"]:
        role_counts[role] += 1


output = {
    "transaction": {
        "signature": signature,
        "slot": slot,
        "timestamp": timestamp,
        "type": tx_type,
        "source": source,
        "fee_payer": fee_payer,
        "description": description,
    },

    "target_mint": TARGET_MINT,

    "summary": {
        "token_transfer_count": len(token_transfers),
        "native_transfer_count": len(native_transfers),
        "instruction_count": len(instructions),
        "program_count": len(program_ids),
        "token_mint_count": len(token_mints),
        "token_account_count": len(token_accounts),
        "token_user_count": len(token_users),
        "participant_account_count": len(role_list),
        "possible_protocol_account_count": len(
            possible_protocol_accounts
        ),
        "role_counts": dict(sorted(role_counts.items())),
    },

    "token_mints": sorted(token_mints),

    "token_accounts": sorted(token_accounts),

    "token_user_accounts": sorted(token_users),

    "program_ids": sorted(program_ids),

    "possible_protocol_accounts": sorted(
        possible_protocol_accounts
    ),

    "participant_candidates": role_list,

    "target_token_transfers": target_token_transfers,

    "raw_native_transfers": native_transfers,

    "raw_token_transfers": token_transfers,
}


# ------------------------------------------------------------
# Print
# ------------------------------------------------------------
print("=" * 70)
print("PARTICIPANT / ACCOUNT ROLE EXTRACTION")
print("=" * 70)

print(f"Signature: {signature}")
print(f"Slot:      {slot}")
print(f"Timestamp: {timestamp}")
print(f"Type:      {tx_type}")
print(f"Source:    {source}")
print(f"Fee payer: {fee_payer}")

if TARGET_MINT:
    print(f"Target mint: {TARGET_MINT}")

print()
print("-" * 70)
print("SUMMARY")
print("-" * 70)

for key, value in output["summary"].items():
    print(f"{key}: {value}")

print()
print("-" * 70)
print("PARTICIPANT CANDIDATES")
print("-" * 70)

for item in role_list:
    print()
    print(item["address"])
    print("  roles:")
    for role in item["roles"]:
        print(f"    - {role}")

    print("  evidence:")
    for evidence in item["evidence"]:
        print(f"    - {evidence}")


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------
OUTPUT_FILE = "participant_roles_output.json"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        indent=2,
        ensure_ascii=False,
    )

print()
print("=" * 70)
print(f"Saved to: {OUTPUT_FILE}")
print("END")
print("=" * 70)