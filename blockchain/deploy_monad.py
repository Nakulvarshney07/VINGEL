"""
blockchain/deploy_monad.py
──────────────────────────
Deploy VingelVault.sol to Monad Testnet.

Prerequisites
─────────────
1. pip3 install web3 py-solc-x
2. Add MONAD_PRIVATE_KEY to your .env  (get testnet MON at https://faucet.monad.xyz)
3. Run: python blockchain/deploy_monad.py

After deployment, copy the printed contract address to .env:
    MONAD_CONTRACT_ADDRESS=0x...
"""

import os
import sys
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines() :
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    # ── Imports ───────────────────────────────────────────────────────────────
    try:
        from web3 import Web3  # type: ignore
    except ImportError:
        print("ERROR: web3 not installed.\n  Run: pip3 install web3")
        sys.exit(1)

    try:
        from solcx import compile_source, install_solc, get_installed_solc_versions  # type: ignore
    except ImportError:
        print("ERROR: py-solc-x not installed.\n  Run: pip3 install py-solc-x")
        sys.exit(1)

    pk = os.environ.get("MONAD_PRIVATE_KEY", "").strip()
    if not pk:
        print("ERROR: MONAD_PRIVATE_KEY not set in .env")
        sys.exit(1)

    rpc = os.environ.get("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")

    # ── Connect ───────────────────────────────────────────────────────────────
    # ── Connect ───────────────────────────────────────────────────────────────
    print(f"Connecting to Monad Testnet at {rpc} ...")
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
    print(f"Wallet:  {acct.address}")
    print(f"Balance: {bal:.4f} MON")

    if bal < 0.001:
        print("\nWARNING: Low balance.")
        print("  Get free testnet MON at https://faucet.monad.xyz")
        print("  Then re-run this script.")
        sys.exit(1)

    # ── Compile ───────────────────────────────────────────────────────────────
    sol_path = Path(__file__).parent / "VingelVault.sol"
    if not sol_path.exists():
        print(f"ERROR: {sol_path} not found")
        sys.exit(1)

    print("\nCompiling VingelVault.sol ...")
    _SOLC = "0.8.20"
    if _SOLC not in [str(v) for v in get_installed_solc_versions()]:
        print(f"  Installing solc {_SOLC} ...")
        install_solc(_SOLC)

    compiled = compile_source(
        sol_path.read_text(),
        output_values=["abi", "bin"],
        solc_version=_SOLC,
    )
    # compiled keys look like "<stdin>:VingelVault"
    contract_key = next(k for k in compiled if "VingelVault" in k)
    abi      = compiled[contract_key]["abi"]
    bytecode = compiled[contract_key]["bin"]
    print("  Compiled OK.")

    # ── Deploy ────────────────────────────────────────────────────────────────
    print("\nDeploying ...")
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
    print(f"  Tx sent:  0x{tx_hash.hex()}")
    print("  Waiting for receipt ...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    addr    = receipt["contractAddress"]

    # ── Result ────────────────────────────────────────────────────────────────
    print(f"\n[SUCCESS] VingelVault deployed!")
    print(f"    Contract:  {addr}")
    print(f"    Gas used:  {receipt['gasUsed']:,}")
    print(f"    Explorer:  https://testnet.monadexplorer.com/address/{addr}")

    # Write address back to .env
    env_text = _env.read_text() if _env.exists() else ""
    if "MONAD_CONTRACT_ADDRESS" in env_text:
        import re
        env_text = re.sub(
            r"MONAD_CONTRACT_ADDRESS=.*",
            f"MONAD_CONTRACT_ADDRESS={addr}",
            env_text,
        )
    else:
        env_text += f"\nMONAD_CONTRACT_ADDRESS={addr}\n"
    _env.write_text(env_text)

    print(f"\n    .env updated:  MONAD_CONTRACT_ADDRESS={addr}")
    print("    Restart the backend to pick up the new address.\n")


if __name__ == "__main__":
    main()
