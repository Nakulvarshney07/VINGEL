"""
blockchain/deploy_simgate.py
─────────────────────────────
Deploy VingelSimGate.sol to Monad Testnet.

Prerequisites
─────────────
1. pip install web3 py-solc-x
2. Add MONAD_PRIVATE_KEY to your .env  (get testnet MON at https://faucet.monad.xyz)
3. Run: python blockchain/deploy_simgate.py

After deployment, the contract address is automatically written to .env as:
    MONAD_SIMGATE_ADDRESS=0x...

Restart the backend to pick up the new address.
"""

import os
import sys
import re
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    # ── Imports ───────────────────────────────────────────────────────────────
    try:
        from web3 import Web3  # type: ignore
    except ImportError:
        print("ERROR: web3 not installed.\n  Run: pip install web3")
        sys.exit(1)

    try:
        from solcx import compile_source, install_solc, get_installed_solc_versions  # type: ignore
    except ImportError:
        print("ERROR: py-solc-x not installed.\n  Run: pip install py-solc-x")
        sys.exit(1)

    pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()
    if not pk:
        print(
            "ERROR: MONAD_PRIVATE_KEY not set in .env\n"
            "  1. Create a wallet and get free testnet MON:\n"
            "     https://faucet.monad.xyz\n"
            "  2. Add to .env:  MONAD_PRIVATE_KEY=0x<your_private_key>"
        )
        sys.exit(1)

    rpc = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")

    # ── Connect ───────────────────────────────────────────────────────────────
    print(f"\n[i] Connecting to Monad Testnet at {rpc} ...")
    w3 = Web3(Web3.HTTPProvider(rpc))
    try:
        from web3.middleware import ExtraDataToPOAMiddleware
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except ImportError:
        pass

    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc}")
        sys.exit(1)

    acct = w3.eth.account.from_key(pk)
    bal  = w3.eth.get_balance(acct.address) / 1e18
    print(f"    Wallet:  {acct.address}")
    print(f"    Balance: {bal:.6f} MON")

    if bal < 0.01:
        print("\n[!] Low balance - need at least 0.01 MON to deploy.")
        print("   Get free testnet MON at https://faucet.monad.xyz")
        sys.exit(1)

    # ── Compile ───────────────────────────────────────────────────────────────
    sol_path = Path(__file__).parent / "VingelSimGate.sol"
    if not sol_path.exists():
        print(f"ERROR: {sol_path} not found")
        sys.exit(1)

    print("\n[*] Compiling VingelSimGate.sol ...")
    _SOLC = "0.8.20"
    installed = [str(v) for v in get_installed_solc_versions()]
    if _SOLC not in installed:
        print(f"    Installing solc {_SOLC} ...")
        install_solc(_SOLC)

    compiled = compile_source(
        sol_path.read_text(),
        output_values=["abi", "bin"],
        solc_version=_SOLC,
    )
    contract_key = next(k for k in compiled if "VingelSimGate" in k)
    abi      = compiled[contract_key]["abi"]
    bytecode = compiled[contract_key]["bin"]
    print("    Compiled OK")

    # ── Deploy ────────────────────────────────────────────────────────────────
    print("\n[*] Deploying VingelSimGate ...")
    factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce   = w3.eth.get_transaction_count(acct.address)

    tx = factory.constructor().build_transaction({
        "chainId":  10143,
        "from":     acct.address,
        "nonce":    nonce,
        "gasPrice": w3.eth.gas_price,
    })
    tx["gas"] = w3.eth.estimate_gas(tx)

    signed  = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"    Tx sent:  0x{tx_hash.hex()}")
    print("    Waiting for receipt ...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    addr    = receipt["contractAddress"]

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n[SUCCESS] VingelSimGate deployed!")
    print(f"    Contract:  {addr}")
    print(f"    Gas used:  {receipt['gasUsed']:,}")
    print(f"    Explorer:  https://testnet.monadexplorer.com/address/{addr}")
    print(f"    Min balance gate: 0.01 MON")

    # ── Write address to .env ─────────────────────────────────────────────────
    env_text = _env_path.read_text() if _env_path.exists() else ""
    if "MONAD_SIMGATE_ADDRESS" in env_text:
        env_text = re.sub(
            r"MONAD_SIMGATE_ADDRESS=.*",
            f"MONAD_SIMGATE_ADDRESS={addr}",
            env_text,
        )
    else:
        env_text += f"\nMONAD_SIMGATE_ADDRESS={addr}\n"
    _env_path.write_text(env_text)

    print(f"\n    .env updated:  MONAD_SIMGATE_ADDRESS={addr}")
    print("    Restart the backend to activate the gated simulation endpoint.\n")


if __name__ == "__main__":
    main()
