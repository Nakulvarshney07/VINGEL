"""Sidebar — navigation, widgets, theme toggle. Returns config dict."""
import streamlit as st

_NAV_PAGES = [
    ("pages/p_overview.py",    "📈", "Overview"),
    ("pages/p_revenue.py",     "💰", "Revenue"),
    ("pages/p_customers.py",   "👥", "Customers"),
    ("pages/p_segments.py",    "🎯", "Segments"),
    ("pages/p_assumptions.py", "⚙️", "Assumptions"),
    ("pages/p_graph.py",       "🌐", "Graph"),
]


def render_sidebar(is_dark: bool = True) -> dict:
    with st.sidebar:

        # ── Logo + theme toggle ──────────────────────────────────────────
        c_logo, c_btn = st.columns([5, 1])
        with c_logo:
            st.markdown(
                '<div class="vg-logo-wrap">'
                '<div><div class="vg-logo-name">VINGEL</div>'
                '<div class="vg-logo-tag">Market Simulator</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )
        with c_btn:
            st.markdown("<div style='padding-top:.35rem'>", unsafe_allow_html=True)
            icon = "☀️" if is_dark else "🌙"
            if st.button(icon, key="_th_toggle", help="Toggle dark / light mode"):
                st.session_state["theme"] = "light" if is_dark else "dark"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="vg-divider"></div>', unsafe_allow_html=True)

        # ── Navigation ───────────────────────────────────────────────────
        st.markdown('<div class="sb-sec">Navigate</div>', unsafe_allow_html=True)
        for path, icon_char, label in _NAV_PAGES:
            st.page_link(path, label=label, icon=icon_char)

        st.markdown('<div class="vg-divider"></div>', unsafe_allow_html=True)

        # ── Product ──────────────────────────────────────────────────────
        st.markdown('<div class="sb-sec">Product</div>', unsafe_allow_html=True)
        
        # Load prefill data with high-fidelity defaults initially
        pf = st.session_state.get("prefill")
        if pf is None:
            pf = {
                "product_name": "ProjectFlow Pro",
                "product_description": "AI-powered project management that auto-schedules tasks, detects bottlenecks, and syncs with Slack/GitHub.",
                "target_market": "SMB software teams, 5-50 employees",
                "price": 49.0,
                "billing_model": "monthly_subscription",
                "geography": ["US", "Canada", "UK"],
                "competitors": ["Asana", "Monday.com", "Linear"],
                "channels": ["Content SEO", "Product-led growth", "Paid LinkedIn"],
                "features": ["AI task scheduling", "Slack integration", "GitHub sync", "Bottleneck alerts", "Team analytics dashboard"]
            }
            st.session_state["prefill"] = pf

        cf = st.session_state.get("prefill_config")
        if cf is None:
            cf = {
                "n_users": 100_000,
                "n_months": 24,
                "n_monte_carlo": 100
            }
            st.session_state["prefill_config"] = cf

        product_name  = st.text_input("Name",        value=pf.get("product_name",""),
                                       placeholder="e.g. ProjectFlow Pro")
        product_desc  = st.text_area("Description",  value=pf.get("product_description",""),
                                      placeholder="What it does · who it's for", height=72)
        target_market = st.text_input("Target Market", value=pf.get("target_market",""),
                                       placeholder="e.g. SMB software teams")
        c1, c2 = st.columns(2)
        with c1:
            price = st.number_input("Price ($)", min_value=0.0,
                                     value=float(pf.get("price", 49.0)), step=5.0)
        with c2:
            _opts = ["monthly_subscription","annual_subscription","one_time","freemium"]
            billing_val = pf.get("billing_model", "monthly_subscription")
            if billing_val not in _opts:
                billing_val = "monthly_subscription"
            billing = st.selectbox(
                "Billing", _opts,
                index=_opts.index(billing_val),
                format_func=lambda x: x.replace("_"," ").title(),
            )

        # ── Market ───────────────────────────────────────────────────────
        st.markdown('<div class="sb-sec">Market</div>', unsafe_allow_html=True)
        geography   = st.text_input("Geography",
                                     value=", ".join(pf.get("geography",[])) or "US, Canada, UK",
                                     placeholder="US, UK, Canada")
        competitors = st.text_input("Competitors",
                                     value=", ".join(pf.get("competitors",[])) or "",
                                     placeholder="Asana, Linear, Monday")
        channels    = st.text_input("Channels",
                                     value=", ".join(pf.get("channels",[])) or "",
                                     placeholder="SEO, PLG, Paid Social")
        features    = st.text_area("Key Features (one per line)",
                                    value="\n".join(pf.get("features",[])) or "",
                                    placeholder="AI scheduling\nSlack integration", height=68)

        # ── Simulation ───────────────────────────────────────────────────
        st.markdown('<div class="sb-sec">Simulation</div>', unsafe_allow_html=True)
        n_users  = st.select_slider("Population",
                                     options=[10_000, 25_000, 50_000, 100_000],
                                     value=cf.get("n_users", 100_000))
        n_months = st.slider("Time horizon (months)", 12, 36, cf.get("n_months", 24))
        n_mc     = st.slider("Monte Carlo runs",      50, 500, cf.get("n_monte_carlo", 100), step=50)

        # Monad Gating Address
        monad_wallet = st.text_input(
            "Monad Wallet Address",
            value=st.session_state.get("monad_wallet", ""),
            placeholder="0x... (Hold ≥ 0.01 MON)",
            help="If provided, simulation runs through the balance-gated on-chain contract.",
            key="monad_wallet_input"
        )
        # Store in session state for other pages
        st.session_state["monad_wallet"] = monad_wallet

        st.markdown("<div style='margin:.75rem 0'></div>", unsafe_allow_html=True)
        run_btn = st.button("Run Simulation →", type="primary", use_container_width=True)

        # ── Vault UI Removed per request ─────────────────────────────────

    return {
        "product_name":   product_name,
        "product_desc":   product_desc,
        "target_market":  target_market,
        "price":          price,
        "billing":        billing,
        "geography":      geography,
        "competitors":    competitors,
        "channels":       channels,
        "features":       features,
        "n_users":        n_users,
        "n_months":       n_months,
        "n_mc":           n_mc,
        "run_btn":        run_btn,
        "vault_owner_id": "",
        "vault_password": "",
        "save_vault_btn": False,
        "monad_wallet":   monad_wallet,
    }
