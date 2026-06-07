"""
VINGEL Market Simulator — REST API  v0.4.0

Simulation
──────────
GET  /health
GET  /api/demo-input
GET  /api/demo
POST /api/assumptions
POST /api/segments
POST /api/simulate/monthly
POST /api/simulate/monte-carlo
POST /api/simulate/full

Blockchain vault
────────────────
POST /api/vault/store
POST /api/vault/load
GET  /api/vault/products/{owner_id}?password=…
GET  /api/vault/chain
GET  /api/vault/verify

Graph (Neo4j)
─────────────
GET  /api/graph/status
GET  /api/graph/nodes?product=…&limit=50
"""
import sys
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.core.config import USE_SARVAM, SARVAM_MODEL, USE_NEO4J, NEO4J_URI, USE_SIMGATE, MONAD_SIMGATE_ADDRESS
from backend.core.models import (
    ProductInput, SimulateRequest, SimulationConfig,
    BusinessAssumptions, CustomerSegment, MonthlyMetrics,
    MonteCarloResult, SimulationResult,
)
from backend.engines.idea_parser import parse_idea
from backend.engines.segmentation import generate_segments
from backend.engines.simulation import generate_population, build_product_params, run_simulation
from backend.engines.monte_carlo import run_monte_carlo
from backend.core.graph import push_population, get_graph_data, is_connected
from blockchain.vault import (
    store_product, load_product, list_products,
    get_public_chain, verify_chain_integrity,
)
from blockchain.monad_client import get_client as _monad, get_simgate_client as _simgate

app = FastAPI(
    title="VINGEL Market Simulator",
    version="0.4.0",
    description="Sarvam AI assumptions · vectorised NumPy funnel · Monte Carlo · Blockchain vault · Neo4j graph",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Demo fixture ──────────────────────────────────────────────────────────────

_DEMO_PRODUCT = ProductInput(
    product_name="ProjectFlow Pro",
    product_description="AI-powered project management that auto-schedules tasks, detects bottlenecks, and syncs with Slack/GitHub.",
    target_market="SMB software teams, 5–50 employees",
    price=49.0,
    billing_model="monthly_subscription",
    geography=["US", "Canada", "UK"],
    competitors=["Asana", "Monday.com", "Linear"],
    channels=["Content SEO", "Product-led growth", "Paid LinkedIn"],
    features=[
        "AI task scheduling",
        "Slack integration",
        "GitHub sync",
        "Bottleneck alerts",
        "Team analytics dashboard",
    ],
)

_DEMO_CONFIG = SimulationConfig(n_users=100_000, n_months=24, n_monte_carlo=100, random_seed=42)


# ── Shared build helper ───────────────────────────────────────────────────────

def _build_result(req: SimulateRequest) -> SimulationResult:
    assumptions, _ = parse_idea(req.product)
    segments, _    = generate_segments(req.product)
    pop     = generate_population(segments, req.config.n_users, seed=req.config.random_seed)
    params  = build_product_params(req.product, assumptions)

    # Monte Carlo (includes base run + base_status)
    mc = run_monte_carlo(pop, params, req.config, segments)

    # Push population + final statuses to Neo4j (fire-and-forget; errors swallowed)
    push_population(req.product.product_name, segments, pop, mc["base_status"])

    base = mc["base_monthly"]
    return SimulationResult(
        product_name=req.product.product_name,
        assumptions=assumptions,
        segments=segments,
        base_monthly=base,
        mc_p10=mc["mc_p10"],
        mc_p50=mc["mc_p50"],
        mc_p90=mc["mc_p90"],
        segment_adoption=mc["segment_adoption"],
        final_mrr=round(base[-1].mrr, 2),
        final_arr=round(base[-1].mrr * 12, 2),
        peak_adoption_rate=round(max(m.adoption_rate for m in base), 4),
        final_churn_rate=round(base[-1].churn_rate, 4),
    )


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    return {
        "status":       "ok",
        "version":      "0.4.0",
        "ai_mode":      f"sarvam ({SARVAM_MODEL})" if USE_SARVAM else "heuristic",
        "neo4j":        "connected" if is_connected() else "unavailable",
        "sim_gate":     f"active ({MONAD_SIMGATE_ADDRESS[:10]}…)" if USE_SIMGATE else "not configured",
        "python":       sys.version,
    }


# ── Demo ──────────────────────────────────────────────────────────────────────

@app.get("/api/demo-input", tags=["demo"])
def demo_input():
    return {"product": _DEMO_PRODUCT.model_dump(), "config": _DEMO_CONFIG.model_dump()}


@app.get("/api/demo", response_model=SimulationResult, tags=["demo"])
def demo():
    return _build_result(SimulateRequest(product=_DEMO_PRODUCT, config=_DEMO_CONFIG))


# ── Step-by-step ──────────────────────────────────────────────────────────────

@app.post("/api/assumptions", tags=["step"])
def get_assumptions(product: ProductInput):
    assumptions, used_sarvam = parse_idea(product)
    return {**assumptions.model_dump(), "_source": "sarvam" if used_sarvam else "heuristic"}


@app.post("/api/segments", tags=["step"])
def get_segments(product: ProductInput):
    segments, used_sarvam = generate_segments(product)
    return {
        "segments": [s.model_dump() for s in segments],
        "_source": "sarvam" if used_sarvam else "heuristic",
    }


@app.post("/api/simulate/monthly", response_model=list[MonthlyMetrics], tags=["simulate"])
def simulate_monthly(req: SimulateRequest):
    assumptions, _ = parse_idea(req.product)
    segments, _    = generate_segments(req.product)
    pop    = generate_population(segments, req.config.n_users, seed=req.config.random_seed)
    params = build_product_params(req.product, assumptions)
    metrics, _ = run_simulation(pop, params, seed=req.config.random_seed, n_months=req.config.n_months)
    return metrics


@app.post("/api/simulate/monte-carlo", response_model=MonteCarloResult, tags=["simulate"])
def simulate_monte_carlo(req: SimulateRequest):
    assumptions, _ = parse_idea(req.product)
    segments, _    = generate_segments(req.product)
    pop    = generate_population(segments, req.config.n_users, seed=req.config.random_seed)
    params = build_product_params(req.product, assumptions)
    mc = run_monte_carlo(pop, params, req.config, segments)
    return MonteCarloResult(
        base_monthly=mc["base_monthly"],
        mc_p10=mc["mc_p10"],
        mc_p50=mc["mc_p50"],
        mc_p90=mc["mc_p90"],
        segment_adoption=mc["segment_adoption"],
    )


@app.post("/api/simulate/full", response_model=SimulationResult, tags=["simulate"])
def simulate_full(req: SimulateRequest):
    return _build_result(req)


# ── Monad-gated simulation ────────────────────────────────────────────────────

import hashlib as _hashlib
import json    as _json


class GatedSimRequest(BaseModel):
    wallet_address: str          # user's Monad wallet to balance-check
    product: ProductInput
    config:  SimulationConfig = SimulationConfig()


@app.post("/api/simulate/gated", tags=["simulate"])
def simulate_gated(req: GatedSimRequest):
    """
    Monad-gated simulation.

    Workflow (when SimGate is configured):
      1. Check user wallet holds ≥ 0.01 MON on Monad testnet.
      2. Call VingelSimGate.requestSimulation() — assigns job_id on-chain.
      3. Run the Sarvam AI + NumPy simulation off-chain.
      4. Call VingelSimGate.storeResult()       — anchors result hash on-chain.
      5. Return full result + job_id + Monad explorer links.

    Graceful degradation:
    - If MONAD_SIMGATE_ADDRESS / MONAD_PRIVATE_KEY are not set → simulation
      still runs; on_chain.gated = false, balance checked read-only.
    - If Monad RPC is unreachable → simulation still runs; balance = None.
    - On-chain steps are individually guarded so one failure never blocks result.
    """
    gate = _simgate()

    # ── Balance check (best-effort, non-blocking when RPC unreachable) ────────
    balance_mon: Optional[float] = None
    rpc_ok = False
    try:
        bal = gate.check_balance(req.wallet_address)
        balance_mon = bal["balance_mon"]
        rpc_ok = True

        # Only hard-fail on insufficient balance when SimGate IS configured
        if gate.is_configured and not bal["ok"]:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Insufficient MON balance. "
                    f"Wallet {req.wallet_address} holds {bal['balance_mon']:.6f} MON — "
                    f"need at least {bal['required_mon']} MON. "
                    f"Get free testnet MON at https://faucet.monad.xyz"
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        # RPC unreachable or address invalid — still run simulation
        balance_mon = None
        rpc_ok = False

    # ── Product hash (fingerprint for on-chain record) ────────────────────────
    product_json = req.product.model_dump_json()
    product_hash = _hashlib.sha256(product_json.encode()).hexdigest()

    # ── On-chain: request simulation (assigns job_id) ─────────────────────────
    sim_gate_mode  = gate.is_configured
    job_id         = None
    request_tx_url = None
    chain_error    = None

    if sim_gate_mode:
        try:
            req_result     = gate.request_simulation(req.wallet_address, product_hash)
            job_id         = req_result["job_id"]
            request_tx_url = req_result["tx_url"]
        except Exception as e:
            chain_error    = str(e)
            # Don't hard-fail — proceed with simulation

    # ── Off-chain: run simulation ─────────────────────────────────────────────
    sim_req = SimulateRequest(product=req.product, config=req.config)
    result  = _build_result(sim_req)

    # ── Result hash ───────────────────────────────────────────────────────────
    result_dict  = result.model_dump()
    result_json  = _json.dumps(result_dict, default=str, sort_keys=True)
    result_hash  = _hashlib.sha256(result_json.encode()).hexdigest()

    # ── On-chain: anchor result hash ──────────────────────────────────────────
    anchor_tx_url = None
    if sim_gate_mode and job_id:
        try:
            anc           = gate.store_result(job_id, result_hash)
            anchor_tx_url = anc["tx_url"]
        except Exception as e:
            anchor_tx_url = f"anchor_error: {e}"

    return {
        **result_dict,
        "on_chain": {
            "job_id":          job_id,
            "product_hash":    product_hash,
            "result_hash":     result_hash,
            "request_tx_url":  request_tx_url,
            "anchor_tx_url":   anchor_tx_url,
            "wallet":          req.wallet_address,
            "balance_mon":     balance_mon,
            "rpc_reachable":   rpc_ok,
            "chain_error":     chain_error,
            "explorer":        "https://testnet.monadexplorer.com",
            "gated":           sim_gate_mode,
        },
    }



@app.get("/api/simulate/verify/{job_id}", tags=["simulate"])
def simulate_verify(job_id: str, result_hash: Optional[str] = None):
    """
    Look up an on-chain simulation job by its job_id.

    Optionally pass ?result_hash=0x… to verify that a specific hash
    matches the one anchored on Monad.
    """
    gate = _simgate()
    try:
        job = gate.get_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    if result_hash:
        try:
            verification = gate.verify_result(job_id, result_hash)
            job["verification"] = verification
        except Exception as e:
            job["verification"] = {"error": str(e)}

    job["explorer_url"] = f"https://testnet.monadexplorer.com/tx/{job_id}"
    return job


@app.get("/api/simulate/user-jobs/{wallet_address}", tags=["simulate"])
def user_jobs(wallet_address: str):
    """Return all simulation job IDs anchored on Monad for a given wallet."""
    gate = _simgate()
    try:
        jobs = gate.get_user_jobs(wallet_address)
        return {"wallet": wallet_address, "count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Blockchain vault ──────────────────────────────────────────────────────────

class VaultStoreRequest(BaseModel):
    product: ProductInput
    owner_id: str
    password: str


class VaultLoadRequest(BaseModel):
    block_hash: str
    owner_id: str
    password: str


@app.post("/api/vault/store", tags=["vault"])
def vault_store(req: VaultStoreRequest):
    try:
        result = store_product(
            product_json=req.product.model_dump_json(),
            owner_id=req.owner_id,
            password=req.password,
        )
        return {
            "success": True,
            "block_hash":   result["block_hash"],
            "timestamp":    result["timestamp"],
            "chain_length": result["chain_length"],
            "message": "Product stored on chain. Save your block_hash to retrieve it later.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vault/load", tags=["vault"])
def vault_load(req: VaultLoadRequest):
    try:
        data = load_product(req.block_hash, req.owner_id, req.password)
        return {"success": True, "product": data}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/products/{owner_id}", tags=["vault"])
def vault_list(owner_id: str, password: str = Query(...)):
    try:
        items = list_products(owner_id, password)
        return {"owner_id": owner_id, "count": len(items), "products": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vault/chain", tags=["vault"])
def vault_chain():
    return {"chain": get_public_chain()}


@app.get("/api/vault/verify", tags=["vault"])
def vault_verify():
    return verify_chain_integrity()


# ── Monad blockchain ──────────────────────────────────────────────────────────
#
# Endpoints
# ─────────
# GET  /api/monad/status                    — RPC connectivity + contract info
# POST /api/monad/publish                   — anchor a local block hash on Monad
# GET  /api/monad/verify/{block_hash}       — check if a hash is on-chain
# GET  /api/monad/blocks/{wallet_address}   — list all hashes anchored by wallet
# GET  /api/monad/balance/{wallet_address}  — MON balance for a wallet


class MonadPublishRequest(BaseModel):
    block_hash: str


@app.get("/api/monad/status", tags=["monad"])
def monad_status():
    """
    Return Monad testnet connectivity info and contract configuration.
    No signing required — safe to call at page load.
    """
    try:
        return _monad().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monad/publish", tags=["monad"])
def monad_publish(req: MonadPublishRequest):
    """
    Anchor a VINGEL local-chain block hash on Monad.

    Requires:
    - MONAD_PRIVATE_KEY in .env
    - MONAD_CONTRACT_ADDRESS in .env (after deploying VingelVault.sol)
    - pip3 install web3
    - Wallet must hold testnet MON (https://faucet.monad.xyz)
    """
    try:
        result = _monad().publish_block(req.block_hash)
        return {"success": True, **result}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monad/verify/{block_hash}", tags=["monad"])
def monad_verify(block_hash: str):
    """
    Call verifyBlock(bytes32) on VingelVault — read-only, no signing.
    Returns whether the hash was anchored, by whom, and when.
    """
    try:
        result = _monad().verify_block(block_hash)
        return {"success": True, **result}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monad/blocks/{wallet_address}", tags=["monad"])
def monad_blocks(wallet_address: str):
    """
    Return all block hashes anchored on Monad by a given wallet — read-only.
    """
    try:
        blocks = _monad().list_blocks(wallet_address)
        return {"wallet": wallet_address, "count": len(blocks), "blocks": blocks}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monad/balance/{wallet_address}", tags=["monad"])
def monad_balance(wallet_address: str):
    """Return MON balance for a wallet (read-only)."""
    try:
        bal = _monad().get_balance(wallet_address)
        return {"wallet": wallet_address, "balance_mon": round(bal, 6)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Graph (Neo4j) ─────────────────────────────────────────────────────────────

@app.get("/api/graph/status", tags=["graph"])
def graph_status():
    """Check whether the Neo4j connection is live."""
    connected = is_connected()
    return {
        "connected": connected,
        "uri":       NEO4J_URI if connected else None,
        "message":   "Neo4j is reachable" if connected
                     else "Neo4j unavailable — start with: docker-compose up -d neo4j",
    }


@app.get("/api/graph/nodes", tags=["graph"])
def graph_nodes(
    product: str = Query(..., description="Product name used in the last simulation"),
    limit:   int = Query(50,  description="Max user nodes to return per segment (default 50)"),
):
    """
    Return product + segment + sampled user nodes for pyvis visualization.
    Queries Neo4j for nodes created during the last simulation run.
    """
    data = get_graph_data(product_name=product, display_per_segment=limit)
    return data
