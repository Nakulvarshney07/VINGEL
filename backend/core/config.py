import os
from dotenv import load_dotenv

load_dotenv()

# ── Sarvam AI ─────────────────────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_MODEL   = os.getenv("SARVAM_MODEL", "sarvam-m")
SARVAM_BASE_URL = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai/v1")
USE_SARVAM     = bool(SARVAM_API_KEY and SARVAM_API_KEY != "your_sarvam_api_key_here")

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "vingel_password")
USE_NEO4J      = os.getenv("USE_NEO4J", "true").lower() not in ("false", "0", "no")

# ── Monad blockchain ──────────────────────────────────────────────────────────
MONAD_RPC_URL          = os.getenv("MONAD_RPC_URL",          "https://testnet-rpc.monad.xyz")
MONAD_CONTRACT_ADDRESS = os.getenv("MONAD_CONTRACT_ADDRESS", "")
MONAD_PRIVATE_KEY      = os.getenv("MONAD_PRIVATE_KEY",      "")

# VingelSimGate — on-chain simulation gating contract
MONAD_SIMGATE_ADDRESS  = os.getenv("MONAD_SIMGATE_ADDRESS",  "")

# Gated simulation is active when both the SimGate contract and private key are set
USE_SIMGATE = bool(MONAD_SIMGATE_ADDRESS and MONAD_PRIVATE_KEY)

# ── Simulation defaults ───────────────────────────────────────────────────────
N_USERS_DEFAULT       = 100_000
N_MONTHS_DEFAULT      = 24
N_MONTE_CARLO_DEFAULT = 100
