"""Vault tab — local encrypted ledger + Monad on-chain anchoring."""
import streamlit as st
import requests
import pandas as pd


_MONAD_EXPLORER_TX   = "https://testnet.monadexplorer.com/tx"
_MONAD_EXPLORER_ADDR = "https://testnet.monadexplorer.com/address"


def render_vault(backend_url: str) -> None:

    # ── Save confirmation (set by app.py after sidebar button) ───────────────
    if "vault_save_ok" in st.session_state:
        hash_val = st.session_state.pop("vault_save_ok")
        st.success("Product stored on local chain — copy your block hash below.")
        st.markdown(f'<div class="vg-hash">{hash_val}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    if "vault_save_err" in st.session_state:
        st.error(st.session_state.pop("vault_save_err"))

    # ════════════════════════════════════════════════════════════════════════
    #  Section 1 — Local encrypted ledger
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="vg-section-head">🔐 Local Encrypted Ledger</div>',
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns(2)

    # Left: decrypt block
    with col_l:
        st.markdown("##### 🔓 Decrypt a Block")
        load_hash  = st.text_input("Block Hash",  placeholder="Full hash from your vault receipt")
        load_owner = st.text_input("Owner ID",    placeholder="your@email.com",  key="vl_owner")
        load_pass  = st.text_input("Password",    type="password",                key="vl_pass")

        if st.button("Decrypt", type="primary", use_container_width=True):
            if not load_hash or not load_owner or not load_pass:
                st.warning("Fill in all three fields.")
            else:
                try:
                    r = requests.post(f"{backend_url}/api/vault/load", json={
                        "block_hash": load_hash,
                        "owner_id":   load_owner,
                        "password":   load_pass,
                    }, timeout=15)
                    if r.status_code == 403:
                        st.error(r.json().get("detail", "Access denied."))
                    elif r.ok:
                        st.success("Decrypted successfully!")
                        st.json(r.json()["product"])
                    else:
                        st.error(r.text)
                except Exception as e:
                    st.error(str(e))

    # Right: list products + chain
    with col_r:
        st.markdown("##### 📦 My Stored Products")
        list_owner = st.text_input("Owner ID",  key="vl_lowner", placeholder="your@email.com")
        list_pass  = st.text_input("Password",  type="password", key="vl_lpass")

        if st.button("List Products", use_container_width=True):
            if not list_owner or not list_pass:
                st.warning("Enter owner ID and password.")
            else:
                try:
                    r = requests.get(f"{backend_url}/api/vault/products/{list_owner}",
                                     params={"password": list_pass}, timeout=15)
                    if r.ok:
                        d = r.json()
                        if d["count"] == 0:
                            st.info("No products found for this owner / password.")
                        else:
                            st.success(f"{d['count']} product(s) found.")
                            for item in d["products"]:
                                ts = pd.Timestamp(item["timestamp"], unit="s").strftime("%Y-%m-%d %H:%M")
                                st.markdown(
                                    f"**{item['product_name']}**  \n"
                                    f"`{item['block_hash'][:26]}…` · {ts}"
                                )
                    else:
                        st.error(r.text)
                except Exception as e:
                    st.error(str(e))

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)

        with c1:
            if st.button("📡 View Chain", use_container_width=True):
                try:
                    r = requests.get(f"{backend_url}/api/vault/chain", timeout=10)
                    r.raise_for_status()
                    chain = r.json().get("chain", [])
                    if not chain:
                        st.info("Chain empty — store your first product.")
                    else:
                        cdf = pd.DataFrame(chain)
                        cdf["timestamp"] = pd.to_datetime(cdf["timestamp"], unit="s")
                        st.dataframe(cdf, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(str(e))

        with c2:
            if st.button("✅ Verify Chain", use_container_width=True):
                try:
                    r = requests.get(f"{backend_url}/api/vault/verify", timeout=10)
                    v = r.json()
                    if v["valid"]:
                        st.success(f"Intact — {v['blocks']} block(s)")
                    else:
                        st.error(f"Broken at block {v['broken_at']}")
                except Exception as e:
                    st.error(str(e))

    st.markdown("<div style='margin:1.5rem 0'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    #  Section 2 — Monad on-chain anchoring
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        '<div class="vg-section-head">⛓️ Monad Blockchain Anchoring</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="vg-section-sub">'
        'Publish a local block hash to Monad testnet — proving it existed at that '
        'timestamp. Encrypted data never leaves your machine; only the hash goes on-chain.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Monad status ──────────────────────────────────────────────────────────
    try:
        sr = requests.get(f"{backend_url}/api/monad/status", timeout=6)
        ms = sr.json() if sr.ok else {}
    except Exception:
        ms = {}

    connected = ms.get("connected", False)
    contract  = ms.get("contract")
    wallet    = ms.get("wallet")
    block_num = ms.get("block_number")
    web3_ok   = ms.get("web3_available", False)

    # Status banner
    if not connected:
        st.warning(
            "⚠️  Cannot reach Monad testnet RPC. "
            "Check your internet connection or the `MONAD_RPC_URL` in `.env`."
        )
    else:
        cols_s = st.columns(4)
        _badge = lambda label, val, ok=True: (
            f'<div style="background:{"rgba(52,211,153,.1)" if ok else "rgba(248,113,113,.1)"}; '
            f'border:1px solid {"#34d399" if ok else "#f87171"}; border-radius:10px; '
            f'padding:10px 14px; text-align:center">'
            f'<div style="font-size:9px;font-weight:800;letter-spacing:.1em;'
            f'text-transform:uppercase;color:{"#34d399" if ok else "#f87171"};margin-bottom:4px">'
            f'{label}</div>'
            f'<div style="font-size:.95rem;font-weight:700;color:var(--t1)">{val}</div></div>'
        )
        cols_s[0].markdown(_badge("Network", "Monad Testnet", True), unsafe_allow_html=True)
        cols_s[1].markdown(_badge("Block", f"#{block_num:,}" if block_num else "—", bool(block_num)), unsafe_allow_html=True)
        cols_s[2].markdown(_badge("Contract", contract[:10] + "…" if contract else "Not deployed", bool(contract)), unsafe_allow_html=True)
        cols_s[3].markdown(_badge("web3.py", "Installed ✓" if web3_ok else "Not installed", web3_ok), unsafe_allow_html=True)

    if not contract:
        with st.expander("⚙️  Setup — Deploy VingelVault.sol"):
            st.markdown("""
**Step 1 — Get testnet MON**
```
https://faucet.monad.xyz
```

**Step 2 — Add your wallet private key to `.env`**
```
MONAD_PRIVATE_KEY=0x...your_private_key...
```

**Step 3 — Install dependencies**
```bash
pip3 install web3 py-solc-x
```

**Step 4 — Deploy the contract**
```bash
python blockchain/deploy_monad.py
```

The script will automatically update `.env` with `MONAD_CONTRACT_ADDRESS`
and print the explorer link. Restart the backend after deployment.
""")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Publish a hash to Monad ───────────────────────────────────────────────
    m1, m2 = st.columns(2)

    with m1:
        st.markdown("##### 🚀 Publish Hash to Monad")
        pub_hash = st.text_input(
            "Local Block Hash",
            placeholder="Paste the SHA-256 hash from your vault receipt",
            key="mn_pub_hash",
        )
        if wallet:
            st.caption(f"Will be published from wallet `{wallet[:10]}…{wallet[-6:]}`")
        else:
            st.caption("Set `MONAD_PRIVATE_KEY` in `.env` to enable publishing.")

        if st.button(
            "⛓️  Anchor on Monad",
            type="primary",
            use_container_width=True,
            disabled=not (connected and contract and bool(pub_hash)),
        ):
            with st.spinner("Sending transaction to Monad …"):
                try:
                    r = requests.post(
                        f"{backend_url}/api/monad/publish",
                        json={"block_hash": pub_hash},
                        timeout=90,
                    )
                    if r.ok:
                        d = r.json()
                        st.success("Anchored on Monad! 🎉")
                        st.markdown(
                            f'<div class="vg-hash">'
                            f'Tx: <a href="{d["tx_url"]}" target="_blank" style="color:#818cf8">'
                            f'{d["tx_hash"][:18]}…</a>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Gas used: {d['gas_used']:,}  ·  Status: {d['status']}")
                    else:
                        detail = r.json().get("detail", r.text)
                        if "web3" in detail.lower():
                            st.error("web3.py not installed.")
                            st.code("pip3 install web3", language="bash")
                        elif "private key" in detail.lower():
                            st.error("Set MONAD_PRIVATE_KEY in .env and restart the backend.")
                        else:
                            st.error(detail)
                except Exception as e:
                    st.error(str(e))

    with m2:
        st.markdown("##### 🔍 Verify on Monad")
        ver_hash = st.text_input(
            "Block Hash to Verify",
            placeholder="Hash to check on-chain",
            key="mn_ver_hash",
        )

        if st.button(
            "Verify On-Chain",
            use_container_width=True,
            disabled=not (connected and contract and bool(ver_hash)),
        ):
            with st.spinner("Querying Monad …"):
                try:
                    r = requests.get(
                        f"{backend_url}/api/monad/verify/{ver_hash}",
                        timeout=15,
                    )
                    if r.ok:
                        d = r.json()
                        if d.get("exists"):
                            ts = pd.Timestamp(d["stored_at"], unit="s").strftime("%Y-%m-%d %H:%M UTC")
                            st.success("✅  Hash found on Monad!")
                            st.markdown(
                                f"**Anchored by:** `{d['owner']}`  \n"
                                f"**At:** {ts}  \n"
                                f"[View wallet on explorer]({d['wallet_url']})"
                            )
                        else:
                            st.warning("Hash not found on Monad — it has not been anchored yet.")
                    else:
                        st.error(r.json().get("detail", r.text))
                except Exception as e:
                    st.error(str(e))

    # ── Browse by wallet ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 🗂️  Browse by Wallet")
    browse_cols = st.columns([3, 1])
    with browse_cols[0]:
        browse_wallet = st.text_input(
            "Wallet Address",
            placeholder="0x...",
            key="mn_browse_wallet",
            value=wallet or "",
        )
    with browse_cols[1]:
        st.markdown("<div style='padding-top:1.7rem'>", unsafe_allow_html=True)
        browse_btn = st.button("Fetch", use_container_width=True,
                               disabled=not (connected and contract and bool(browse_wallet)))
        st.markdown("</div>", unsafe_allow_html=True)

    if browse_btn and browse_wallet:
        with st.spinner("Querying Monad …"):
            try:
                # balance + blocks in parallel
                rb = requests.get(f"{backend_url}/api/monad/balance/{browse_wallet}", timeout=10)
                rh = requests.get(f"{backend_url}/api/monad/blocks/{browse_wallet}",  timeout=15)

                if rb.ok:
                    bal = rb.json().get("balance_mon", 0)
                    st.caption(f"Balance: **{bal:.4f} MON**  ·  "
                               f"[Explorer]({_MONAD_EXPLORER_ADDR}/{browse_wallet})")

                if rh.ok:
                    d = rh.json()
                    n = d.get("count", 0)
                    if n == 0:
                        st.info("No hashes anchored by this wallet yet.")
                    else:
                        st.success(f"{n} hash(es) anchored on Monad.")
                        for bh in d.get("blocks", []):
                            short = f"{bh[:18]}…{bh[-6:]}"
                            tx_link = f"{_MONAD_EXPLORER_ADDR}/{browse_wallet}"
                            st.markdown(
                                f"<code style='font-size:.8rem'>{short}</code> "
                                f"[↗]({tx_link})",
                                unsafe_allow_html=True,
                            )
                else:
                    st.error(rh.text)
            except Exception as e:
                st.error(str(e))
