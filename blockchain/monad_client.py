"""
blockchain/monad_client.py
──────────────────────────
Monad blockchain integration for VINGEL.

Architecture
────────────
• VingelVault.sol is deployed to Monad testnet (see deploy_monad.py).
• After a product is stored in the local ledger (vault.py), its block hash
  can be "anchored" on Monad — proving it existed at a given point in time.
• The encrypted product data NEVER leaves the user's machine.

Read-only methods (verifyBlock, listBlocks, getBalance) use direct JSON-RPC
calls via requests — no extra dependencies needed.

Write methods (publishBlock) require web3.py for ECDSA transaction signing:
    pip3 install web3

Monad Testnet
─────────────
  RPC:      https://testnet-rpc.monad.xyz
  Chain ID: 10143
  Symbol:   MON
  Explorer: https://testnet.monadexplorer.com
  Faucet:   https://faucet.monad.xyz

Environment variables (.env)
────────────────────────────
  MONAD_RPC_URL            (default: https://testnet-rpc.monad.xyz)
  MONAD_CONTRACT_ADDRESS   (set after deploying VingelVault.sol)
  MONAD_PRIVATE_KEY        (wallet private key — NEVER commit this)
"""

from __future__ import annotations

import os
import requests as _req
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

MONAD_RPC      = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
MONAD_CHAIN_ID = 10143
EXPLORER_TX    = "https://testnet.monadexplorer.com/tx"
EXPLORER_ADDR  = "https://testnet.monadexplorer.com/address"

CONTRACT_ADDR = os.environ.get("MONAD_CONTRACT_ADDRESS", "")
PRIVATE_KEY   = os.environ.get("MONAD_PRIVATE_KEY", "")


# ── Pure-Python Keccak-256 ────────────────────────────────────────────────────
# Ethereum uses Keccak-256 — NOT FIPS SHA3-256 (different padding: 0x01 vs 0x06).
# This implementation is needed to compute EVM function selectors without web3.

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [ 0, 36,  3, 41, 18],
    [ 1, 44, 10, 45,  2],
    [62,  6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39,  8, 14],
]
_M64 = 0xFFFFFFFFFFFFFFFF


def _rot64(v: int, r: int) -> int:
    return ((v << r) | (v >> (64 - r))) & _M64


def _keccak_f(A: list) -> list:
    for rc in _RC:
        # θ
        C = [A[x][0] ^ A[x][1] ^ A[x][2] ^ A[x][3] ^ A[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rot64(C[(x + 1) % 5], 1) for x in range(5)]
        A = [[A[x][y] ^ D[x] for y in range(5)] for x in range(5)]
        # ρ + π
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rot64(A[x][y], _ROT[x][y])
        # χ
        A = [
            [(B[x][y] ^ (~B[(x + 1) % 5][y] & B[(x + 2) % 5][y])) & _M64
             for y in range(5)]
            for x in range(5)
        ]
        # ι
        A[0][0] ^= rc
    return A


def _keccak256(data: bytes) -> bytes:
    """Ethereum-compatible Keccak-256 — pure Python, no dependencies."""
    _RATE = 136  # 1088-bit rate for 256-bit capacity
    buf = bytearray(data)
    pad = _RATE - (len(buf) % _RATE)
    buf += bytearray(pad)
    buf[-pad] ^= 0x01   # Keccak padding (0x01 != SHA3's 0x06)
    buf[-1]   ^= 0x80

    A = [[0] * 5 for _ in range(5)]
    for i in range(0, len(buf), _RATE):
        block = buf[i: i + _RATE]
        for j in range(17):  # 17 lanes × 8 bytes = 136 bytes
            A[j % 5][j // 5] ^= int.from_bytes(block[j * 8: j * 8 + 8], "little")
        A = _keccak_f(A)

    out = bytearray()
    for y in range(5):
        for x in range(5):
            out += A[x][y].to_bytes(8, "little")
    return bytes(out[:32])


# ── Minimal ABI encoder / decoder ─────────────────────────────────────────────

def _selector(sig: str) -> bytes:
    """4-byte EVM function selector from a Solidity signature string."""
    return _keccak256(sig.encode())[:4]


def _enc_bytes32(value: bytes) -> bytes:
    if len(value) > 32:
        raise ValueError("bytes32 overflow")
    return value.ljust(32, b"\x00")


def _enc_address(addr: str) -> bytes:
    raw = bytes.fromhex(addr.removeprefix("0x"))
    return raw.rjust(32, b"\x00")


def _dec_bool(data: bytes, offset: int = 0) -> bool:
    return bool(int.from_bytes(data[offset: offset + 32], "big"))


def _dec_address(data: bytes, offset: int = 0) -> str:
    return "0x" + data[offset + 12: offset + 32].hex()


def _dec_uint256(data: bytes, offset: int = 0) -> int:
    return int.from_bytes(data[offset: offset + 32], "big")


def _dec_bytes32_array(data: bytes) -> list[str]:
    """Decode ABI-encoded bytes32[] returned by eth_call."""
    if len(data) < 64:
        return []
    arr_off = _dec_uint256(data, 0)
    count   = _dec_uint256(data, arr_off)
    out = []
    for i in range(count):
        start = arr_off + 32 + i * 32
        out.append("0x" + data[start: start + 32].hex())
    return out


# Pre-compute function selectors (evaluated once at import time)
_SEL_STORE  = _selector("storeBlock(bytes32)")
_SEL_VERIFY = _selector("verifyBlock(bytes32)")
_SEL_OWNER  = _selector("getOwnerBlocks(address)")
_SEL_COUNT  = _selector("getBlockCount(address)")


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _rpc(method: str, params: list, rpc_url: str = MONAD_RPC):
    resp = _req.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"RPC error {body['error'].get('code')}: {body['error'].get('message')}")
    return body.get("result")


def _eth_call(to: str, data: bytes, rpc_url: str) -> bytes:
    hex_data = "0x" + data.hex()
    result   = _rpc("eth_call", [{"to": to, "data": hex_data}, "latest"], rpc_url)
    if not result or result == "0x":
        return b""
    return bytes.fromhex(result.removeprefix("0x"))


# ── MonadClient ───────────────────────────────────────────────────────────────

class MonadClient:
    """
    Python client for VingelVault on Monad testnet.

    Read-only calls (verify_block, list_blocks, get_balance) use pure
    JSON-RPC — no extra dependencies.

    Write calls (publish_block) need web3.py:  pip3 install web3
    """

    def __init__(
        self,
        rpc_url:       Optional[str] = None,
        contract_addr: Optional[str] = None,
        private_key:   Optional[str] = None,
    ):
        self.rpc_url  = rpc_url or os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        self.contract = (contract_addr or os.environ.get("MONAD_CONTRACT_ADDRESS", "")).lower().strip()
        self.pk       = (private_key or os.environ.get("MONAD_PRIVATE_KEY", "")).strip()
        self._last_pk = self.pk
        self._w3      = None
        self._acct    = None

        if self.pk and self.contract:
            self._init_web3()

    def _init_web3(self):
        if not self.rpc_url:
            self.rpc_url = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        if not self.contract:
            self.contract = os.environ.get("MONAD_CONTRACT_ADDRESS", "").lower().strip()
        if not self.pk:
            self.pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()

        if not self.pk:
            return

        try:
            from web3 import Web3  # type: ignore
            w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 15}))
            try:
                from web3.middleware import ExtraDataToPOAMiddleware  # type: ignore
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except ImportError:
                pass
            self._w3   = w3
            self._acct = w3.eth.account.from_key(self.pk)
        except ImportError:
            pass  # web3 not installed — write calls will raise a clear error

    # ── Status ────────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        try:
            return _rpc("eth_blockNumber", [], self.rpc_url) is not None
        except Exception:
            return False

    def web3_available(self) -> bool:
        try:
            import web3  # noqa: F401
            return True
        except ImportError:
            return False

    def get_status(self) -> dict:
        connected = self.is_connected()
        block_num = None
        if connected:
            try:
                block_num = int(_rpc("eth_blockNumber", [], self.rpc_url), 16)
            except Exception:
                pass
        wallet = self.wallet_address()
        return {
            "connected":      connected,
            "block_number":   block_num,
            "chain_id":       MONAD_CHAIN_ID,
            "rpc_url":        self.rpc_url,
            "contract":       self.contract or None,
            "wallet":         wallet,
            "has_private_key": bool(self.pk),
            "web3_available": self.web3_available(),
            "explorer":       "https://testnet.monadexplorer.com",
        }

    # ── Read (no signing — pure JSON-RPC) ─────────────────────────────────────

    def get_balance(self, address: str) -> float:
        """Return MON balance in ether units."""
        wei = int(_rpc("eth_getBalance", [address, "latest"], self.rpc_url), 16)
        return wei / 1e18

    def verify_block(self, block_hash_hex: str) -> dict:
        """
        Call verifyBlock(bytes32) on the contract.

        Returns:
            exists    bool   — was this hash ever anchored?
            owner     str    — wallet that anchored it
            stored_at int    — Unix timestamp
            wallet_url str   — Monad explorer link for the owner wallet
        """
        if not self.contract:
            raise RuntimeError(
                "MONAD_CONTRACT_ADDRESS not set. "
                "Deploy VingelVault.sol first: python blockchain/deploy_monad.py"
            )
        bh       = bytes.fromhex(block_hash_hex.removeprefix("0x"))
        raw      = _eth_call(self.contract, _SEL_VERIFY + _enc_bytes32(bh), self.rpc_url)
        if len(raw) < 96:
            return {"exists": False, "owner": None, "stored_at": None, "wallet_url": None}

        exists    = _dec_bool(raw, 0)
        owner     = _dec_address(raw, 32)
        stored_at = _dec_uint256(raw, 64)
        return {
            "exists":     exists,
            "owner":      owner if exists else None,
            "stored_at":  stored_at if exists else None,
            "wallet_url": f"{EXPLORER_ADDR}/{owner}" if exists else None,
        }

    def list_blocks(self, wallet_address: str) -> list[str]:
        """
        Call getOwnerBlocks(address) — returns list of block hash hex strings
        that the given wallet has anchored on Monad.
        """
        if not self.contract:
            raise RuntimeError(
                "MONAD_CONTRACT_ADDRESS not set. "
                "Deploy VingelVault.sol first: python blockchain/deploy_monad.py"
            )
        raw = _eth_call(
            self.contract,
            _SEL_OWNER + _enc_address(wallet_address),
            self.rpc_url,
        )
        return _dec_bytes32_array(raw)

    def get_block_count(self, wallet_address: str) -> int:
        """How many hashes has this wallet anchored on Monad?"""
        if not self.contract:
            return 0
        raw = _eth_call(
            self.contract,
            _SEL_COUNT + _enc_address(wallet_address),
            self.rpc_url,
        )
        return _dec_uint256(raw) if raw else 0

    # ── Write (requires web3 + private key) ───────────────────────────────────

    def publish_block(self, block_hash_hex: str) -> dict:
        """
        Send storeBlock(bytes32) transaction to VingelVault on Monad.

        Requires:
          1. pip3 install web3
          2. MONAD_PRIVATE_KEY set in .env
          3. Wallet has testnet MON (https://faucet.monad.xyz)

        Returns:
            tx_hash   str   — transaction hash
            tx_url    str   — Monad explorer URL
            gas_used  int
            status    str   — 'success' or 'failed'
        """
        if not self.contract:
            raise RuntimeError(
                "MONAD_CONTRACT_ADDRESS not set. "
                "Deploy VingelVault.sol first: python blockchain/deploy_monad.py"
            )
        if not self.pk:
            raise RuntimeError(
                "MONAD_PRIVATE_KEY not configured.\n"
                "Add it to your .env file. Never commit private keys."
            )
        if not self.web3_available():
            raise RuntimeError(
                "web3.py not installed.\n"
                "Run:  pip3 install web3\n"
                "Then restart the backend."
            )

        if not self.contract:
            self.contract = os.environ.get("MONAD_CONTRACT_ADDRESS", "").lower().strip()
        if not self.pk:
            self.pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()

        # Lazily init web3 if it was installed after startup or key changed
        if self._w3 is None or self.pk != self._last_pk:
            self._last_pk = self.pk
            self._init_web3()
        if self._w3 is None:
            raise RuntimeError("web3 init failed — check your RPC URL and private key.")

        # Check balance of backend signing wallet
        try:
            bal = self._w3.eth.get_balance(self._acct.address) / 1e18
            if bal <= 0:
                raise RuntimeError(
                    f"Backend wallet ({self._acct.address}) has 0 MON.\n"
                    f"Please fund it with testnet MON at https://faucet.monad.xyz to pay for transaction gas."
                )
        except Exception as e:
            if "has 0 MON" in str(e):
                raise e
            pass

        from web3 import Web3

        w3       = self._w3
        acct     = self._acct
        bh_bytes = bytes.fromhex(block_hash_hex.removeprefix("0x"))

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.contract),
            abi=_VAULT_ABI,
        )
        nonce   = w3.eth.get_transaction_count(acct.address)
        gas_p   = w3.eth.gas_price

        tx = contract.functions.storeBlock(bh_bytes).build_transaction({
            "chainId":  MONAD_CHAIN_ID,
            "from":     acct.address,
            "nonce":    nonce,
            "gasPrice": gas_p,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)

        signed  = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        return {
            "tx_hash":    tx_hash.hex(),
            "tx_url":     f"{EXPLORER_TX}/{tx_hash.hex()}",
            "block_hash": block_hash_hex,
            "gas_used":   receipt["gasUsed"],
            "status":     "success" if receipt["status"] == 1 else "failed",
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def wallet_address(self) -> Optional[str]:
        """Derive the wallet address from MONAD_PRIVATE_KEY (read-only, no RPC)."""
        if not self.pk:
            return None
        if self._acct:
            return self._acct.address
        try:
            from web3 import Web3  # type: ignore
            return Web3().eth.account.from_key(self.pk).address
        except Exception:
            return None

    def tx_url(self, tx_hash: str) -> str:
        return f"{EXPLORER_TX}/{tx_hash}"

    def addr_url(self, address: str) -> str:
        return f"{EXPLORER_ADDR}/{address}"


# ── Minimal ABI for VingelVault ───────────────────────────────────────────────

_VAULT_ABI = [
    {
        "name": "storeBlock",
        "type": "function",
        "inputs":  [{"name": "blockHash", "type": "bytes32"}],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "verifyBlock",
        "type": "function",
        "inputs":  [{"name": "blockHash", "type": "bytes32"}],
        "outputs": [
            {"name": "exists",   "type": "bool"},
            {"name": "owner",    "type": "address"},
            {"name": "storedAt", "type": "uint256"},
        ],
        "stateMutability": "view",
    },
    {
        "name": "getOwnerBlocks",
        "type": "function",
        "inputs":  [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
    },
    {
        "name": "getBlockCount",
        "type": "function",
        "inputs":  [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "type": "event",
        "name": "BlockStored",
        "inputs": [
            {"name": "owner",     "type": "address", "indexed": True},
            {"name": "blockHash", "type": "bytes32", "indexed": True},
            {"name": "storedAt",  "type": "uint256", "indexed": False},
        ],
    },
]



# ── Module-level singleton ────────────────────────────────────────────────────

_client: Optional[MonadClient] = None


def get_client() -> MonadClient:
    """Return the shared MonadClient instance (lazy init)."""
    global _client
    if _client is None:
        _client = MonadClient()
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# SimGateClient — VingelSimGate.sol integration
# ─────────────────────────────────────────────────────────────────────────────

SIMGATE_ADDR = os.environ.get("MONAD_SIMGATE_ADDRESS", "")

# Pre-compute selectors for VingelSimGate functions
_SEL_REQUEST = _selector("requestSimulation(address,bytes32)")
_SEL_STORE_R = _selector("storeResult(bytes32,bytes32)")
_SEL_GET_JOB = _selector("getJob(bytes32)")
_SEL_VERIFY_R = _selector("verifyResult(bytes32,bytes32)")
_SEL_USER_JOBS = _selector("getUserJobs(address)")

# Minimal ABI for VingelSimGate
_SIMGATE_ABI = [
    {
        "name": "requestSimulation",
        "type": "function",
        "inputs": [
            {"name": "user",        "type": "address"},
            {"name": "productHash", "type": "bytes32"},
        ],
        "outputs": [{"name": "jobId", "type": "bytes32"}],
        "stateMutability": "nonpayable",
    },
    {
        "name": "storeResult",
        "type": "function",
        "inputs": [
            {"name": "jobId",      "type": "bytes32"},
            {"name": "resultHash", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "getJob",
        "type": "function",
        "inputs": [{"name": "jobId", "type": "bytes32"}],
        "outputs": [
            {"name": "user",        "type": "address"},
            {"name": "productHash", "type": "bytes32"},
            {"name": "resultHash",  "type": "bytes32"},
            {"name": "requestedAt", "type": "uint256"},
            {"name": "completedAt", "type": "uint256"},
            {"name": "completed",   "type": "bool"},
        ],
        "stateMutability": "view",
    },
    {
        "name": "verifyResult",
        "type": "function",
        "inputs": [
            {"name": "jobId",      "type": "bytes32"},
            {"name": "resultHash", "type": "bytes32"},
        ],
        "outputs": [
            {"name": "matches",  "type": "bool"},
            {"name": "storedAt", "type": "uint256"},
        ],
        "stateMutability": "view",
    },
    {
        "name": "getUserJobs",
        "type": "function",
        "inputs": [{"name": "user", "type": "address"}],
        "outputs": [{"name": "", "type": "bytes32[]"}],
        "stateMutability": "view",
    },
    {
        "type": "event",
        "name": "SimulationRequested",
        "inputs": [
            {"name": "jobId",       "type": "bytes32", "indexed": True},
            {"name": "user",        "type": "address", "indexed": True},
            {"name": "productHash", "type": "bytes32", "indexed": False},
            {"name": "requestedAt", "type": "uint256", "indexed": False},
        ],
    },
    {
        "type": "event",
        "name": "SimulationCompleted",
        "inputs": [
            {"name": "jobId",      "type": "bytes32", "indexed": True},
            {"name": "resultHash", "type": "bytes32", "indexed": False},
            {"name": "completedAt","type": "uint256", "indexed": False},
        ],
    },
    {
        "name": "MIN_BALANCE",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "pure",
    },
]


class SimGateClient:
    """
    Python client for VingelSimGate.sol on Monad testnet.

    This wraps the on-chain simulation gating contract:

        requestSimulation(user, productHash) — balance-check + job creation
        storeResult(jobId, resultHash)       — anchor result hash (owner only)
        getJob(jobId)                        — read job details
        verifyResult(jobId, resultHash)      — verify a result hash

    All write calls require web3.py (pip install web3) and MONAD_PRIVATE_KEY.
    All read calls use pure JSON-RPC — no extra deps.
    """

    def __init__(
        self,
        rpc_url:      Optional[str] = None,
        contract_addr: Optional[str] = None,
        private_key:  Optional[str] = None,
    ):
        self.rpc_url  = rpc_url or os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        self.contract = (contract_addr or os.environ.get("MONAD_SIMGATE_ADDRESS", "")).strip()
        self.pk       = (private_key or os.environ.get("MONAD_PRIVATE_KEY", "")).strip()
        self._last_pk = self.pk
        self._w3      = None
        self._acct    = None

        if self.pk and self.contract:
            self._init_web3()

    def _init_web3(self):
        if not self.rpc_url:
            self.rpc_url = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        if not self.contract:
            self.contract = os.environ.get("MONAD_SIMGATE_ADDRESS", "").strip()
        if not self.pk:
            self.pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()

        if not self.pk:
            return

        try:
            from web3 import Web3  # type: ignore
            w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 15}))
            try:
                from web3.middleware import ExtraDataToPOAMiddleware  # type: ignore
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            except ImportError:
                pass
            self._w3   = w3
            self._acct = w3.eth.account.from_key(self.pk)
        except ImportError:
            pass

    @property
    def is_configured(self) -> bool:
        return bool(self.contract and self.pk)

    # ── Balance check (pure JSON-RPC — no deps) ───────────────────────────────

    def check_balance(self, user_address: str) -> dict:
        """
        Check whether user_address holds the minimum required MON balance.

        Returns:
            ok          bool    — True if user can run a gated simulation
            balance_mon float   — user's current MON balance
            required_mon float  — minimum required (0.01 MON)
            user        str     — the checked address
        """
        try:
            wei = int(_rpc("eth_getBalance", [user_address, "latest"], self.rpc_url), 16)
        except Exception as e:
            raise RuntimeError(f"Could not fetch balance for {user_address}: {e}")

        balance_mon  = wei / 1e18
        required_mon = 0.01  # MIN_BALANCE in contract = 0.01 ether
        return {
            "ok":           balance_mon >= required_mon,
            "balance_mon":  round(balance_mon, 6),
            "required_mon": required_mon,
            "user":         user_address,
        }

    # ── Read (pure JSON-RPC) ──────────────────────────────────────────────────

    def get_job(self, job_id_hex: str) -> dict:
        """
        Read job details from VingelSimGate.

        Returns dict with: user, product_hash, result_hash,
                           requested_at, completed_at, completed,
                           job_id, explorer_url
        """
        if not self.contract:
            raise RuntimeError("MONAD_SIMGATE_ADDRESS not set. Run: python blockchain/deploy_simgate.py")

        bh  = bytes.fromhex(job_id_hex.removeprefix("0x"))
        raw = _eth_call(self.contract, _SEL_GET_JOB + _enc_bytes32(bh), self.rpc_url)

        if len(raw) < 192:
            return {"error": "job_not_found", "job_id": job_id_hex}

        user        = _dec_address(raw, 0)
        product_hash = "0x" + raw[32:64].hex()
        result_hash  = "0x" + raw[64:96].hex()
        requested_at = _dec_uint256(raw, 96)
        completed_at = _dec_uint256(raw, 128)
        completed    = _dec_bool(raw, 160)

        return {
            "job_id":       job_id_hex,
            "user":         user,
            "product_hash": product_hash,
            "result_hash":  result_hash if completed else None,
            "requested_at": requested_at,
            "completed_at": completed_at if completed else None,
            "completed":    completed,
            "explorer_url": f"{EXPLORER_TX}/{job_id_hex}",
        }

    def verify_result(self, job_id_hex: str, result_hash_hex: str) -> dict:
        """
        Call verifyResult(jobId, resultHash) on VingelSimGate.

        Returns:
            matches   bool   — True if the hash matches the on-chain record
            stored_at int    — Unix timestamp when result was anchored (0 if no match)
        """
        if not self.contract:
            raise RuntimeError("MONAD_SIMGATE_ADDRESS not set.")

        jb  = bytes.fromhex(job_id_hex.removeprefix("0x"))
        rh  = bytes.fromhex(result_hash_hex.removeprefix("0x"))
        raw = _eth_call(
            self.contract,
            _SEL_VERIFY_R + _enc_bytes32(jb) + _enc_bytes32(rh),
            self.rpc_url,
        )

        if len(raw) < 64:
            return {"matches": False, "stored_at": None}

        return {
            "matches":   _dec_bool(raw, 0),
            "stored_at": _dec_uint256(raw, 32) or None,
        }

    def get_user_jobs(self, user_address: str) -> list[str]:
        """Return all job IDs for a given user wallet."""
        if not self.contract:
            return []
        raw = _eth_call(
            self.contract,
            _SEL_USER_JOBS + _enc_address(user_address),
            self.rpc_url,
        )
        return _dec_bytes32_array(raw)

    # ── Write (requires web3 + private key) ──────────────────────────────────

    def _require_web3(self):
        if not self.contract:
            self.contract = os.environ.get("MONAD_SIMGATE_ADDRESS", "").strip()
        if not self.pk:
            self.pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()

        if not self.pk:
            raise RuntimeError(
                "MONAD_PRIVATE_KEY not configured.\n"
                "Add it to your .env file. Never commit private keys."
            )
        if not self.contract:
            raise RuntimeError(
                "MONAD_SIMGATE_ADDRESS not set.\n"
                "Deploy the contract first: python blockchain/deploy_simgate.py"
            )
        try:
            import web3  # type: ignore # noqa: F401
        except ImportError:
            raise RuntimeError(
                "web3.py not installed.\n"
                "Run: pip install web3\nThen restart the backend."
            )
        if self._w3 is None or self.pk != self._last_pk:
            self._last_pk = self.pk
            self._init_web3()
        if self._w3 is None:
            raise RuntimeError("web3 init failed — check MONAD_RPC_URL and MONAD_PRIVATE_KEY.")

        # Check balance of backend signing wallet
        try:
            bal = self._w3.eth.get_balance(self._acct.address) / 1e18
            if bal <= 0:
                raise RuntimeError(
                    f"Backend wallet ({self._acct.address}) has 0 MON.\n"
                    f"Please fund it with testnet MON at https://faucet.monad.xyz to pay for transaction gas."
                )
        except Exception as e:
            if "has 0 MON" in str(e):
                raise e
            pass

    def request_simulation(self, user_address: str, product_hash_hex: str) -> dict:
        """
        Call requestSimulation(user, productHash) on VingelSimGate.

        The contract will:
          1. Revert with InsufficientBalance if user holds < 0.01 MON.
          2. Assign a unique job_id and emit SimulationRequested.

        Returns:
            job_id      str   — bytes32 hex job identifier
            tx_hash     str   — transaction hash
            tx_url      str   — Monad explorer link
            gas_used    int
        """
        self._require_web3()

        from web3 import Web3  # type: ignore

        w3   = self._w3
        acct = self._acct

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.contract),
            abi=_SIMGATE_ABI,
        )

        nonce = w3.eth.get_transaction_count(acct.address)
        ph    = bytes.fromhex(product_hash_hex.removeprefix("0x"))

        tx = contract.functions.requestSimulation(
            Web3.to_checksum_address(user_address),
            ph,
        ).build_transaction({
            "chainId":  MONAD_CHAIN_ID,
            "from":     acct.address,
            "nonce":    nonce,
            "gasPrice": w3.eth.gas_price,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)

        signed  = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] != 1:
            raise RuntimeError("requestSimulation transaction reverted — user likely has insufficient balance.")

        # Extract jobId from SimulationRequested event
        job_id = None
        try:
            logs = contract.events.SimulationRequested().process_receipt(receipt)
            if logs:
                job_id = "0x" + logs[0]["args"]["jobId"].hex()
        except Exception:
            pass

        # Fallback: derive job_id from tx logs raw data
        if not job_id and receipt.get("logs"):
            job_id = "0x" + receipt["logs"][0]["topics"][1].hex() if len(receipt["logs"][0].get("topics", [])) > 1 else None

        return {
            "job_id":   job_id,
            "tx_hash":  "0x" + tx_hash.hex(),
            "tx_url":   f"{EXPLORER_TX}/0x{tx_hash.hex()}",
            "gas_used": receipt["gasUsed"],
            "status":   "success",
        }

    def store_result(self, job_id_hex: str, result_hash_hex: str) -> dict:
        """
        Call storeResult(jobId, resultHash) on VingelSimGate.
        Anchors the simulation result hash permanently on-chain.

        Returns:
            tx_hash   str
            tx_url    str
            gas_used  int
            status    str  — 'success' or 'failed'
        """
        self._require_web3()

        from web3 import Web3  # type: ignore

        w3   = self._w3
        acct = self._acct

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.contract),
            abi=_SIMGATE_ABI,
        )

        nonce = w3.eth.get_transaction_count(acct.address)
        jb    = bytes.fromhex(job_id_hex.removeprefix("0x"))
        rh    = bytes.fromhex(result_hash_hex.removeprefix("0x"))

        tx = contract.functions.storeResult(jb, rh).build_transaction({
            "chainId":  MONAD_CHAIN_ID,
            "from":     acct.address,
            "nonce":    nonce,
            "gasPrice": w3.eth.gas_price,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)

        signed  = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        return {
            "tx_hash":  "0x" + tx_hash.hex(),
            "tx_url":   f"{EXPLORER_TX}/0x{tx_hash.hex()}",
            "gas_used": receipt["gasUsed"],
            "status":   "success" if receipt["status"] == 1 else "failed",
        }


# ── SimGateClient singleton ───────────────────────────────────────────────────

_simgate: Optional["SimGateClient"] = None


def get_simgate_client() -> "SimGateClient":
    """Return the shared SimGateClient instance (lazy init)."""
    global _simgate
    if _simgate is None:
        _simgate = SimGateClient()
    return _simgate

