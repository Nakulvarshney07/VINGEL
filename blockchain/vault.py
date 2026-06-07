"""
blockchain/vault.py

Local blockchain simulation for product data privacy.

Architecture:
  - Product JSON is encrypted with owner's password (AES-256 via Fernet)
  - Encrypted blob is stored as a "block" in a local JSON ledger
  - Each block contains: hash, prev_hash, owner_id, encrypted_data, timestamp
  - Only someone with the correct owner_id + password can decrypt
  - Chain integrity is maintained via prev_hash linkage

To connect to a real blockchain (Polygon/Ethereum):
  - Replace ledger read/write with Web3.py contract calls
  - Replace Fernet encryption with ECIES (secp256k1 via MetaMask key)
"""

import json
import hashlib
import os
import time
import base64
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    from blockchain._crypto_compat import Fernet, InvalidToken, PBKDF2HMAC

    class hashes:  # noqa: N801
        class SHA256:
            pass

LEDGER_PATH = Path(__file__).parent / "ledger.json"


# ── Key derivation ─────────────────────────────────────────────────────────────

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    raw = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(raw)


# ── Ledger I/O ─────────────────────────────────────────────────────────────────

def _load() -> dict:
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return {"chain": [], "index": {}}


def _save(ledger: dict) -> None:
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


# ── Block building ─────────────────────────────────────────────────────────────

def _build_block(owner_id: str, encrypted_b64: str, salt_b64: str, prev_hash: str) -> dict:
    ts = int(time.time())
    raw = f"{owner_id}{encrypted_b64}{ts}{prev_hash}".encode()
    block_hash = hashlib.sha256(raw).hexdigest()
    return {
        "hash":           block_hash,
        "prev_hash":      prev_hash,
        "owner_id":       owner_id,
        "encrypted_data": encrypted_b64,
        "salt":           salt_b64,
        "timestamp":      ts,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def store_product(product_json: str, owner_id: str, password: str) -> dict:
    """
    Encrypt product data and append a new block to the ledger.

    Parameters
    ----------
    product_json : str   Raw JSON string of ProductInput
    owner_id     : str   Any unique identifier for the owner (email, wallet, username)
    password     : str   Secret known only to the owner — used for encryption key derivation

    Returns
    -------
    dict  { block_hash, timestamp, chain_length }
    """
    salt      = os.urandom(16)
    key       = _derive_key(password, salt)
    fernet    = Fernet(key)
    encrypted = fernet.encrypt(product_json.encode())

    ledger    = _load()
    prev_hash = ledger["chain"][-1]["hash"] if ledger["chain"] else "0" * 64

    block = _build_block(
        owner_id     = owner_id,
        encrypted_b64= base64.b64encode(encrypted).decode(),
        salt_b64     = base64.b64encode(salt).decode(),
        prev_hash    = prev_hash,
    )

    ledger["chain"].append(block)

    # Index: owner_id → list of block hashes (no data exposed)
    ledger["index"].setdefault(owner_id, [])
    if block["hash"] not in ledger["index"][owner_id]:
        ledger["index"][owner_id].append(block["hash"])

    _save(ledger)

    return {
        "block_hash":    block["hash"],
        "timestamp":     block["timestamp"],
        "chain_length":  len(ledger["chain"]),
    }


def load_product(block_hash: str, owner_id: str, password: str) -> dict:
    """
    Decrypt and return product data for the block owner.

    Raises ValueError if block_hash not found OR password is wrong (owner mismatch).
    This mirrors smart-contract behaviour: wrong caller = revert.
    """
    ledger = _load()
    block  = next((b for b in ledger["chain"] if b["hash"] == block_hash), None)

    if block is None:
        raise ValueError("Block not found on chain.")

    if block["owner_id"] != owner_id:
        raise ValueError("Access denied — you are not the owner of this block.")

    salt      = base64.b64decode(block["salt"])
    key       = _derive_key(password, salt)
    fernet    = Fernet(key)

    try:
        encrypted = base64.b64decode(block["encrypted_data"])
        plaintext = fernet.decrypt(encrypted)
        return json.loads(plaintext)
    except (InvalidToken, Exception):
        raise ValueError("Decryption failed — invalid password.")


def list_products(owner_id: str, password: str) -> list[dict]:
    """
    Return metadata for all blocks owned by owner_id (verifies password on each).
    Does NOT return the full product data — only name + hash + timestamp.
    """
    ledger    = _load()
    hashes    = ledger["index"].get(owner_id, [])
    results   = []

    for bh in hashes:
        try:
            data = load_product(bh, owner_id, password)
            results.append({
                "block_hash":   bh,
                "product_name": data.get("product_name", "Unknown"),
                "timestamp":    next(b["timestamp"] for b in ledger["chain"] if b["hash"] == bh),
            })
        except Exception:
            pass  # wrong password skips silently

    return results


def get_public_chain() -> list[dict]:
    """
    Return the public chain — hashes + timestamps only, no encrypted data.
    Demonstrates transparency + immutability without exposing any content.
    """
    ledger = _load()
    return [
        {
            "block_number": i + 1,
            "hash":         b["hash"][:16] + "…",
            "prev_hash":    b["prev_hash"][:16] + "…",
            "owner_id":     b["owner_id"][:4] + "****",   # masked
            "timestamp":    b["timestamp"],
        }
        for i, b in enumerate(ledger["chain"])
    ]


def verify_chain_integrity() -> dict:
    """Check that every block correctly links to its predecessor."""
    ledger = _load()
    chain  = ledger["chain"]

    if not chain:
        return {"valid": True, "blocks": 0, "message": "Empty chain"}

    broken_at = None
    for i in range(1, len(chain)):
        if chain[i]["prev_hash"] != chain[i - 1]["hash"]:
            broken_at = i
            break

    return {
        "valid":    broken_at is None,
        "blocks":   len(chain),
        "broken_at": broken_at,
        "message":  "Chain intact" if broken_at is None else f"Chain broken at block {broken_at}",
    }
