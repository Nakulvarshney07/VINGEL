# VINGEL — Market Simulator

**Created by: Sumit Kumar, Aman Mishra, and Nakul Varshney**

Turn any product idea into a data-driven market forecast in under 30 seconds.

**Sarvam AI** generates assumptions and customer segments · **NumPy vectorized engine** runs 100k synthetic users through a 24-month adoption funnel · **Monte Carlo** produces P10/P50/P90 revenue uncertainty bands · **Monad blockchain** anchors simulation hashes on-chain (via API) · **Neo4j graph** visualises the population live.

---

## Quick Start

```bash
# 1. Copy and fill in optional API keys
cp .env.example .env

# 2. Install all dependencies
./run.sh install

# 3. Start backend + frontend together
./run.sh both
```

- Frontend: **http://localhost:8501**
- API docs: **http://localhost:8000/docs**

---

## UI — Multi-Page Navigation

The frontend is a multi-page Streamlit app. A sidebar navigation section links all pages. The KPI row and result header appear on every page after a simulation runs.

| Page | URL | Contents |
|------|-----|----------|
| 📈 Overview | `/` | Landing page or results overview + segment chart |
| 💰 Revenue | `/revenue` | MRR line chart + P10/P50/P90 band + cumulative chart |
| 👥 Customers | `/customers` | Active customers over time + new-vs-churned bar chart |
| 🎯 Segments | `/segments` | Adoption per segment + behavioral parameters table |
| ⚙️ Assumptions | `/assumptions` | 8 AI-generated KPIs + product profile radar chart |
| 🌐 Graph | `/graph` | Live Neo4j population graph rendered with pyvis |

---

## Optional Features

| Feature | Requires | What it enables |
|---------|----------|-----------------|
| Sarvam AI | `SARVAM_API_KEY` in `.env` | AI-generated TAM, churn, virality, 4 custom segments |
| Monad blockchain | `MONAD_PRIVATE_KEY` + deployed contract | On-chain proof of simulation hash |
| Local vault | Nothing extra | Encrypt + store product inputs; only you can decrypt |
| Neo4j graph | Neo4j Desktop running | Population nodes pushed to graph DB; interactive viz |

All are optional — the simulator runs fully offline with heuristic stubs.

---

## Project Structure

```
VINGEL/
├── backend/
│   ├── core/
│   │   ├── config.py            Environment variables + feature flags
│   │   ├── models.py            Pydantic schemas for all I/O
│   │   └── graph.py             Neo4j push + query helpers
│   ├── engines/
│   │   ├── idea_parser.py       ProductInput → BusinessAssumptions (Sarvam AI or heuristic)
│   │   ├── segmentation.py      ProductInput → 4 CustomerSegments  (Sarvam AI or heuristic)
│   │   ├── simulation.py        Population generation + 24-month funnel loop
│   │   └── monte_carlo.py       100-run MC wrapper → P10 / P50 / P90
│   ├── main.py                  FastAPI app — all endpoints
│   └── requirements.txt
├── blockchain/
│   ├── vault.py                 AES-256 encryption + local chain ledger
│   ├── _crypto_compat.py        Pure-stdlib fallback (no cryptography package needed)
│   ├── monad_client.py          Monad testnet client (pure-Python Keccak-256, no web3 for reads)
│   ├── VingelVault.sol          Solidity contract for on-chain hash anchoring
│   └── deploy_monad.py          One-command contract deployment script
├── frontend/
│   ├── app.py                   Entry point — navigation, shared sidebar, simulation runner
│   ├── pages/
│   │   ├── p_overview.py        Landing page / results overview
│   │   ├── p_revenue.py         Revenue charts
│   │   ├── p_customers.py       Customer charts
│   │   ├── p_segments.py        Segment analysis
│   │   ├── p_assumptions.py     Business assumptions
│   │   ├── p_vault.py           Local + Monad vault
│   │   └── p_graph.py           Neo4j graph
│   ├── components/
│   │   ├── styles.py            CSS injection + JS effects (dark / light theme)
│   │   ├── sidebar.py           Sidebar widgets + page navigation + theme toggle
│   │   ├── landing.py           Hero, feature cards, stats row, CTA
│   │   ├── kpi_row.py           Animated JS counter KPI cards
│   │   ├── charts.py            Shared Plotly theme helper
│   │   ├── tab_revenue.py       Revenue charts component
│   │   ├── tab_customers.py     Customers charts component
│   │   ├── tab_segments.py      Segments component
│   │   ├── tab_assumptions.py   Assumptions component
│   │   ├── tab_vault.py         Vault component (local + Monad)
│   │   └── tab_graph.py         Neo4j / pyvis graph component
│   └── requirements.txt
├── run.sh                       One-command launcher
├── .env.example                 Config template
└── README.md
```

---

## Run Commands

```bash
./run.sh install     # install all dependencies (first time only)
./run.sh both        # start backend + frontend together
./run.sh backend     # start FastAPI only   → http://localhost:8000
./run.sh frontend    # start Streamlit only → http://localhost:8501
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in what you need:

```bash
# Sarvam AI (optional)
SARVAM_API_KEY=your_sarvam_api_key_here
SARVAM_MODEL=sarvam-m                  # default

# Neo4j graph (optional)
NEO4J_URI=bolt://localhost:7687        # default
NEO4J_USER=neo4j                       # default
NEO4J_PASSWORD=vingel_password         # match your Neo4j DB password
USE_NEO4J=true                         # set false to disable

# Monad blockchain (optional)
MONAD_RPC_URL=https://testnet-rpc.monad.xyz    # default (Monad testnet)
MONAD_CONTRACT_ADDRESS=0x...           # filled in automatically by deploy_monad.py
MONAD_PRIVATE_KEY=0x...               # your wallet private key for publishing
```

---

## API Endpoints

### System

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, version, AI mode, Neo4j connection |

### Demo

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/demo-input` | Pre-filled `ProductInput` + `SimulationConfig` |
| `GET` | `/api/demo` | Full simulation result for the demo product |

### Step-by-step

| Method | Path | Input → Output |
|--------|------|----------------|
| `POST` | `/api/assumptions` | `ProductInput` → `BusinessAssumptions` + `_source` |
| `POST` | `/api/segments` | `ProductInput` → `list[CustomerSegment]` + `_source` |

### Simulation

| Method | Path | Input → Output |
|--------|------|----------------|
| `POST` | `/api/simulate/monthly` | `SimulateRequest` → `list[MonthlyMetrics]` |
| `POST` | `/api/simulate/monte-carlo` | `SimulateRequest` → `MonteCarloResult` |
| `POST` | `/api/simulate/full` | `SimulateRequest` → `SimulationResult` |

### Blockchain Vault (local)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/vault/store` | Encrypt product input and write a new chain block |
| `POST` | `/api/vault/load` | Decrypt a block (owner + password required) |
| `GET` | `/api/vault/products/{owner_id}?password=…` | List all blocks owned by you |
| `GET` | `/api/vault/chain` | Public chain — hashes and timestamps only |
| `GET` | `/api/vault/verify` | Verify chain hash-linkage integrity |

### Monad Blockchain

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/monad/status` | Network connection, block number, contract and web3 status |
| `POST` | `/api/monad/publish` | Anchor a block hash on Monad testnet (requires private key) |
| `GET` | `/api/monad/verify/{block_hash}` | Check if a hash was anchored and by whom |
| `GET` | `/api/monad/blocks/{wallet_address}` | List all hashes anchored by a wallet |
| `GET` | `/api/monad/balance/{wallet_address}` | Get MON balance for a wallet |

### Neo4j Graph

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/graph/status` | Neo4j connection check |
| `GET` | `/api/graph/nodes?product=…&limit=50` | Sampled population nodes for visualization |

---

## Monad Blockchain Integration

*Note: The Vault and Verify UI tabs were removed to streamline the dashboard, but the underlying Monad blockchain anchoring system remains fully functional via API.*

You can anchor a simulation's SHA-256 block hash on the Monad testnet, creating cryptographic proof that your analysis existed at a specific point in time. Only the hash goes on-chain — encrypted data never leaves your machine.

### Smart contract — `VingelVault.sol`

Deployed on **Monad Testnet** (Chain ID: 10143, RPC: `https://testnet-rpc.monad.xyz`).

```solidity
function storeBlock(bytes32 blockHash) external
function verifyBlock(bytes32 blockHash) external view
    returns (bool exists, address owner, uint256 storedAt)
function getOwnerBlocks(address owner) external view returns (bytes32[] memory)
function getBlockCount(address owner) external view returns (uint256)
```

Event: `BlockStored(address indexed owner, bytes32 indexed blockHash, uint256 storedAt)`

### Deploy the contract

```bash
# 1. Get testnet MON from the faucet
#    https://faucet.monad.xyz

# 2. Add your private key to .env
echo "MONAD_PRIVATE_KEY=0x..." >> .env

# 3. Install deployment dependencies
pip3 install web3 py-solc-x

# 4. Deploy (compiles VingelVault.sol and writes address to .env automatically)
python blockchain/deploy_monad.py
```

### Read-only mode (no private key needed)

`monad_client.py` uses raw JSON-RPC with pure-Python Keccak-256 for all read operations. Verifying hashes and browsing wallets works without web3.py installed. Only publishing requires a private key and web3.

---

## Local Blockchain Vault

**File:** `blockchain/vault.py` + `blockchain/_crypto_compat.py`

Product inputs can be encrypted and stored as blocks on a local chain ledger (`blockchain/ledger.json`). No third-party service — everything runs locally. Works without the `cryptography` package via a pure-stdlib HMAC-SHA256 fallback.

### How it works

1. **Key derivation** — PBKDF2-HMAC-SHA256 (200,000 iterations), random 16-byte salt
2. **Encryption** — Fernet AES-128-CBC + HMAC-SHA256 (or pure-stdlib CTR fallback)
3. **Block creation** — SHA-256 hash chain linking owner ID, encrypted blob, timestamp, and previous hash
4. **Ledger** — blocks appended to `blockchain/ledger.json`

### Block structure

```json
{
  "hash":           "sha256(owner_id + encrypted_data + timestamp + prev_hash)",
  "prev_hash":      "hash of the previous block",
  "owner_id":       "your@email.com",
  "encrypted_data": "base64-encoded ciphertext",
  "salt":           "base64-encoded 16-byte salt",
  "timestamp":      1234567890
}
```

---

## How the Simulation Works

```
Product Idea
     │
     ▼
┌──────────────────────┐
│  Step 1              │  idea_parser.py
│  Parse Assumptions   │  → TAM, churn, virality, marketing reach …
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 2              │  segmentation.py
│  Generate Segments   │  → 4 customer segments with behavioral parameters
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 3              │  simulation.py → generate_population()
│  Build Population    │  → 100,000 synthetic users as NumPy arrays
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 4              │  simulation.py → run_simulation()
│  Monthly Funnel      │  → 24-month status evolution (unaware→aware→active→churned)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 5              │  monte_carlo.py
│  Monte Carlo         │  → 100 runs with varied parameters → P10/P50/P90
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 6              │  graph.py → Neo4j (optional)
│  Graph Push          │  → 2,000 sampled user nodes + segment/product nodes
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 7              │  FastAPI → Streamlit
│  Results             │  → MRR, ARR, adoption, churn, segments, graph, vault
└──────────────────────┘
```

### Step 1 — Parse Assumptions

**With Sarvam AI key** — sends product details to `sarvam-m`, gets back a JSON object with all parameters. Falls back to heuristics automatically on any error.

**Without Sarvam AI key** — pure heuristic rules:

| Input signal | What it drives |
|---|---|
| `billing_model = freemium` | TAM = 2M, virality = 1.10 |
| `price < $20` | TAM = 1M |
| `price $20–$100` | TAM = 300k |
| `price $100–$500` | TAM = 80k |
| `price > $500` | TAM = 20k |

Output — `BusinessAssumptions`:

```
total_addressable_market   integer    realistic number of potential users
problem_severity           0–1        how urgent/painful the problem is
feature_match              0–1        how well features solve the core need
switching_cost             0–1        friction to leave existing tools
brand_recognition          0.02–0.25  initial awareness for a new entrant
virality_coefficient       0–2.0      word-of-mouth growth factor
monthly_marketing_reach    0.005–0.06 fraction of TAM reached per month
churn_rate_monthly         0.01–0.15  monthly customer churn rate
```

### Step 2 — Customer Segments

**With Sarvam AI** — Tailored segments based on the product. **Without** — B2B or consumer defaults expanded to **8 diverse segments** for rich, beautiful graph data:

| Example Segments | Share | Profile |
|---------|-------|---------|
| Power Users / Early Adopters | 10-15% | High urgency, low trust barrier |
| Pragmatic Professionals | 25-40% | Moderate values, social-proof driven |
| Value Seekers / Bargain Hunters | 20-30% | High price sensitivity, need clear ROI |
| Trendsetters & Innovators | 5-10% | Highly networked, testing bleeding-edge tech |
| Skeptical Traditionalists | 5-10% | Deeply loyal to legacy software, hard to convert |
| Late Majority | 10-15% | Low tech affinity, high competitor loyalty |

### Step 3 — Synthetic Population (100k users)

Each user gets attributes sampled from normal distributions around their segment's mean (σ = 0.12):

```python
price_sensitivity, need_level, trust_score, income_monthly
purchase_threshold ~ Beta(2.5, 2.5)   # personal bar to convert
churn_threshold    ~ Beta(4.0, 2.0)   # personal tolerance before leaving
```

### Step 4 — Monthly Funnel Loop

Status transitions: `0=Unaware → 1=Aware → 2=Active → 3=Churned`

**Awareness**: `P(aware) = clip(marketing_reach + wom_rate, 0, 0.8)`

**Conversion** (vectorized purchase score):
```
PurchaseScore = 0.30×need_fit + 0.20×feature_match + 0.15×trust
              + 0.10×peer_influence + 0.15×affordability
              − 0.20×competitor_loyalty − 0.15×switching_cost
```
Passed through `sigmoid(4×score − 3)` → monthly conversion probability.

**Churn**: `churn_prob = base_churn × (1 − 0.5×affordability + 0.3×competitor_loyalty)`

### Step 5 — Monte Carlo (100 runs)

Parameters perturbed ±15–40% per run. Results in P10/P50/P90 revenue bands per month.

---

## Dependencies

### Backend

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn[standard]` | ASGI server |
| `numpy>=2.1.0` | Vectorized simulation |
| `pandas>=2.2.3` | Data manipulation |
| `pydantic==2.9.2` | Schema validation |
| `python-dotenv` | `.env` loading |
| `openai>=1.0.0` | Sarvam AI via OpenAI-compatible SDK (optional) |
| `cryptography>=42.0.0` | AES-256 vault (optional — stdlib fallback included) |
| `neo4j>=5.0.0` | Neo4j driver (optional) |

### Frontend

| Package | Purpose |
|---------|---------|
| `streamlit==1.41.0` | Multi-page web dashboard |
| `plotly==5.24.1` | Interactive charts |
| `requests` | Backend API calls |
| `pandas` | Table rendering |
| `pyvis>=0.3.2` | Neo4j graph visualization |

### Blockchain (optional)

| Package | Purpose |
|---------|---------|
| `web3` | Transaction signing for Monad publish |
| `py-solc-x` | Solidity compilation for contract deploy |

---

## Demo Product

The built-in demo simulates **ProjectFlow Pro** — an AI-powered project management SaaS:

```
Price:       $49 / month
Market:      SMB software teams, 5–50 employees
Geography:   US, Canada, UK
Competitors: Asana, Monday.com, Linear
Channels:    Content SEO, Product-led growth, Paid LinkedIn
Features:    AI task scheduling, Slack integration, GitHub sync,
             Bottleneck alerts, Team analytics dashboard
```

Run from the UI: **⚡ Quick Demo** button on the Overview page, or hit the API directly:

```bash
curl http://localhost:8000/api/demo | python3 -m json.tool
```
