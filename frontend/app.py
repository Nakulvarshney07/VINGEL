import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd

from components.styles   import inject_styles, inject_effects
from components.sidebar  import render_sidebar
from components.kpi_row  import render_kpi_row


def _build_sim_animation_html(is_dark: bool, n_users: int = 100_000) -> str:
    bg = "#07070c" if is_dark else "#f0f0f8"
    tc = "#55556a" if is_dark else "#9090b0"
    target = n_users
    target_label = f"{n_users // 1000}k" if n_users >= 1000 else str(n_users)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:100%;height:100%;background:{bg};overflow:hidden}}
canvas{{position:absolute;inset:0;width:100%;height:100%}}
#title{{position:absolute;top:14px;left:50%;transform:translateX(-50%);
  font:700 10px/1 'Inter',sans-serif;letter-spacing:.14em;text-transform:uppercase;
  color:#818cf8;white-space:nowrap}}
#lbl{{position:absolute;bottom:14px;left:50%;transform:translateX(-50%);
  font:600 10px/1 'Inter',sans-serif;letter-spacing:.09em;text-transform:uppercase;
  color:{tc};white-space:nowrap}}
#counter{{position:absolute;top:14px;right:18px;
  font:700 11px/1 'Inter',sans-serif;letter-spacing:.05em;
  color:#34d399;white-space:nowrap}}
</style></head><body>
<canvas id="gc"></canvas>
<div id="title">◉ Building Population Graph</div>
<div id="counter">0 / {target_label}</div>
<div id="lbl" id="lbl">Initialising…</div>
<script>
(function(){{
  const cv=document.getElementById('gc');
  const cx=cv.getContext('2d');
  function resize(){{cv.width=cv.offsetWidth;cv.height=cv.offsetHeight;}}
  resize();
  window.addEventListener('resize',resize);

  const COLS=['#818cf8','#34d399','#fbbf24','#f472b6'];
  const ANGS=[3.93,5.50,2.36,0.79];
  const MAX_PARTICLES=240;
  const TARGET_USERS={target};
  const TARGET_LABEL='{target_label}';
  let tick=0;
  let simCount=0;

  const segs=ANGS.map((a,i)=>{{
    const r=Math.min(cv.width,cv.height)*0.31;
    return{{
      x:cv.width/2+r*Math.cos(a),y:cv.height/2+r*Math.sin(a),
      c:COLS[i],op:0,r:15
    }};
  }});

  const users=[];

  function spawnUser(){{
    const si=Math.floor(Math.random()*4);
    const s=segs[si];
    if(s.op<0.4)return;
    const a=Math.random()*Math.PI*2,d=28+Math.random()*80;
    const u={{
      x:s.x+Math.cos(a)*d,y:s.y+Math.sin(a)*d,
      c:s.c,r:1.6+Math.random()*3,op:0,life:0,
      maxLife:200+Math.random()*200,
      vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,
      si:si
    }};
    if(users.length>=MAX_PARTICLES){{
      users.shift();
    }}
    users.push(u);
  }}

  function hex2(n){{return Math.max(0,Math.min(255,Math.round(n))).toString(16).padStart(2,'0');}}

  function drawConnections(){{
    const n=Math.min(users.length,70);
    for(let i=0;i<n;i++){{
      for(let j=i+1;j<n;j++){{
        const dx=users[i].x-users[j].x,dy=users[i].y-users[j].y;
        const dist=Math.sqrt(dx*dx+dy*dy);
        if(dist<60){{
          const alpha=Math.floor((1-dist/60)*users[i].op*users[j].op*32);
          cx.beginPath();cx.moveTo(users[i].x,users[i].y);cx.lineTo(users[j].x,users[j].y);
          cx.strokeStyle=users[i].c+hex2(alpha);cx.lineWidth=0.6;cx.stroke();
        }}
      }}
    }}
  }}

  function draw(){{
    cx.clearRect(0,0,cv.width,cv.height);
    tick++;
    const cx2=cv.width/2,cy2=cv.height/2;

    segs.forEach((s,i)=>{{
      const st=55+i*28;
      if(tick>=st)s.op=Math.min(1,(tick-st)/18);
    }});

    // Always spawn — particles recycle, animation never stops
    if(tick>110&&tick%2===0){{
      spawnUser();
      if(simCount<TARGET_USERS){{
        const pct=simCount/TARGET_USERS;
        const speed=pct<0.05?200:(pct<0.25?140:(pct<0.60?80:(pct<0.90?40:12)));
        simCount=Math.min(TARGET_USERS,simCount+speed);
      }}
    }}

    segs.forEach(s=>{{
      if(s.op<.01)return;
      cx.beginPath();cx.moveTo(cx2,cy2);cx.lineTo(s.x,s.y);
      cx.strokeStyle=s.c+hex2(s.op*55);cx.lineWidth=1.4;cx.stroke();
    }});

    drawConnections();

    for(let i=users.length-1;i>=0;i--){{
      const u=users[i];
      u.life++;
      const fadeIn=Math.min(1,u.life/30);
      const fadeOut=u.life>u.maxLife*0.75?1-((u.life-u.maxLife*0.75)/(u.maxLife*0.25)):1;
      u.op=fadeIn*fadeOut;
      u.x+=u.vx;u.y+=u.vy;
      const seg=segs[u.si];
      u.vx+=(seg.x-u.x)*0.00015;
      u.vy+=(seg.y-u.y)*0.00015;
      cx.beginPath();cx.arc(u.x,u.y,u.r,0,Math.PI*2);
      cx.fillStyle=u.c+hex2(u.op*200);cx.fill();
      if(u.life>u.maxLife)users.splice(i,1);
    }}

    segs.forEach(s=>{{
      if(s.op<.01)return;
      const g=cx.createRadialGradient(s.x,s.y,0,s.x,s.y,s.r*3.2);
      g.addColorStop(0,s.c+hex2(s.op*70));g.addColorStop(1,s.c+'00');
      cx.beginPath();cx.arc(s.x,s.y,s.r*3.2,0,Math.PI*2);cx.fillStyle=g;cx.fill();
      cx.beginPath();cx.arc(s.x,s.y,s.r*(1+.05*Math.sin(tick*.06)),0,Math.PI*2);
      cx.fillStyle=s.c+hex2(s.op*255);cx.fill();
    }});

    const pulse=1+.07*Math.sin(tick*.045);
    const pr=24*pulse;
    const og=cx.createRadialGradient(cx2,cy2,0,cx2,cy2,pr*2.8);
    og.addColorStop(0,'#f59e0b55');og.addColorStop(1,'#f59e0b00');
    cx.beginPath();cx.arc(cx2,cy2,pr*2.8,0,Math.PI*2);cx.fillStyle=og;cx.fill();
    const ig=cx.createRadialGradient(cx2-5,cy2-5,2,cx2,cy2,pr);
    ig.addColorStop(0,'#fde68a');ig.addColorStop(1,'#f59e0b');
    cx.beginPath();cx.arc(cx2,cy2,pr,0,Math.PI*2);cx.fillStyle=ig;cx.fill();

    const lbl=document.getElementById('lbl');
    const ctr=document.getElementById('counter');
    if(lbl){{
      if(tick<55)lbl.textContent='Initialising product node…';
      else if(users.length<8)lbl.textContent='Building customer segments…';
      else if(simCount<1000)lbl.textContent='Mapping synthetic population…';
      else if(simCount<TARGET_USERS)lbl.textContent='Running Monte Carlo scenarios…';
      else lbl.textContent='Simulation complete — finalising results…';
    }}
    if(ctr){{
      const k=simCount>=1000?(simCount/1000).toFixed(1)+'k':simCount.toLocaleString();
      ctr.textContent=k+' / '+TARGET_LABEL;
    }}

    requestAnimationFrame(draw);
  }}
  draw();
}})();
</script></body></html>"""

BACKEND = "http://localhost:8000"

st.set_page_config(
    page_title="VINGEL — Market Simulator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

_PAGES = [
    st.Page("pages/p_overview.py",    title="Overview",    icon="📈", default=True),
    st.Page("pages/p_revenue.py",     title="Revenue",     icon="💰"),
    st.Page("pages/p_customers.py",   title="Customers",   icon="👥"),
    st.Page("pages/p_segments.py",    title="Segments",    icon="🎯"),
    st.Page("pages/p_assumptions.py", title="Assumptions", icon="⚙️"),
    st.Page("pages/p_vault.py",       title="Vault",       icon="🔒"),
    st.Page("pages/p_graph.py",       title="Graph",       icon="🌐"),
    st.Page("pages/p_verify.py",      title="Verify",      icon="🔍"),
]

pg = st.navigation(_PAGES, position="hidden")

is_dark = st.session_state.get("theme", "dark") == "dark"
inject_styles(is_dark)
inject_effects()
cfg = render_sidebar(is_dark)

# ── Vault save ────────────────────────────────────────────────────────────────
if cfg["save_vault_btn"]:
    payload = st.session_state.get("payload", {})
    if payload.get("product"):
        try:
            resp = requests.post(f"{BACKEND}/api/vault/store", json={
                "product":  payload["product"],
                "owner_id": cfg["vault_owner_id"],
                "password": cfg["vault_password"],
            }, timeout=15)
            resp.raise_for_status()
            d = resp.json()
            st.session_state["vault_save_ok"] = f"Block #{d['chain_length']} — {d['block_hash']}"
        except Exception as e:
            st.session_state["vault_save_err"] = str(e)

# ── Run simulation ────────────────────────────────────────────────────────────
if cfg["run_btn"]:
    payload = {
        "product": {
            "product_name":        cfg["product_name"],
            "product_description": cfg["product_desc"],
            "target_market":       cfg["target_market"],
            "price":               cfg["price"],
            "billing_model":       cfg["billing"],
            "geography":   [g.strip() for g in cfg["geography"].split(",")   if g.strip()],
            "competitors":  [c.strip() for c in cfg["competitors"].split(",") if c.strip()],
            "channels":    [c.strip() for c in cfg["channels"].split(",")    if c.strip()],
            "features":    [f.strip() for f in cfg["features"].splitlines()  if f.strip()],
        },
        "config": {
            "n_users":       cfg["n_users"],
            "n_months":      cfg["n_months"],
            "n_monte_carlo": cfg["n_mc"],
            "random_seed":   42,
        },
    }

    col_log, col_graph = st.columns([5, 6])

    with col_graph:
        components.html(_build_sim_animation_html(is_dark, n_users=cfg["n_users"]), height=440)

    with col_log:
        with st.status("Running VINGEL simulation…", expanded=True) as sim_status:
            st.write("🤖  Calling Sarvam AI — generating market assumptions and 4 customer segments…")
            try:
                wallet = cfg.get("monad_wallet", "").strip()
                if wallet:
                    st.write(f"💜  On-chain Simulation Gating — Checking MON balance & requesting job on Monad…")
                    gated_payload = {
                        "wallet_address": wallet,
                        "product": payload["product"],
                        "config": payload["config"]
                    }
                    resp = requests.post(f"{BACKEND}/api/simulate/gated", json=gated_payload, timeout=120)
                else:
                    resp = requests.post(f"{BACKEND}/api/simulate/full", json=payload, timeout=120)
                resp.raise_for_status()
            except requests.exceptions.ConnectionError:
                sim_status.update(label="Backend not running", state="error")
                st.error("Start the backend first: `./run.sh backend`")
                st.stop()
            except requests.exceptions.HTTPError as he:
                sim_status.update(label="Simulation failed", state="error")
                try:
                    err_msg = he.response.json().get("detail", str(he))
                except Exception:
                    err_msg = str(he)
                st.error(f"Error: {err_msg}")
                st.stop()
            except Exception as e:
                sim_status.update(label="Simulation failed", state="error")
                st.error(str(e))
                st.stop()

            result = resp.json()
            st.session_state["result"]  = result
            st.session_state["payload"] = payload

            n_u  = payload["config"]["n_users"]
            n_m  = payload["config"]["n_months"]
            n_mc = payload["config"]["n_monte_carlo"]
            st.write(
                f"⚡  Simulation complete — "
                f"{n_u:,} users · {n_m}-month funnel · {n_mc} Monte Carlo runs"
            )

            # Show Monad on-chain result summary
            on_chain = result.get("on_chain")
            if on_chain:
                if on_chain.get("job_id"):
                    bal = on_chain.get("balance_mon")
                    bal_str = f" · {bal:.4f} MON" if bal is not None else ""
                    st.write(f"💜  Monad anchored — Job: `{on_chain['job_id'][:18]}…`{bal_str}")
                elif on_chain.get("rpc_reachable"):
                    bal = on_chain.get("balance_mon")
                    st.write(f"🟢  Monad connected — balance: {bal:.4f} MON · SimGate not deployed (hashes computed locally)")
                else:
                    st.write("🟡  Monad RPC unreachable — simulation ran locally (blockchain not required)")

            st.write("🌐  Pushing population nodes to Neo4j — building graph…")
            try:
                gr = requests.get(
                    f"{BACKEND}/api/graph/nodes",
                    params={"product": payload["product"]["product_name"], "limit": 50},
                    timeout=30,
                )
                gd = gr.json() if gr.ok else {"source": "unavailable"}
            except Exception:
                gd = {"source": "unavailable"}
            st.session_state["graph_data"] = gd

            if gd.get("source") not in ("unavailable", "not_found", None) and \
                    not str(gd.get("source", "")).startswith("error"):
                n_nodes = gd.get("total_stored", len(gd.get("users", [])))
                st.write(f"✅  Graph ready — {n_nodes:,} population nodes")
            else:
                st.write("⚠️  Neo4j unavailable — graph skipped (start Neo4j Desktop to enable)")

            sim_status.update(label="Simulation complete!", state="complete", expanded=False)

    st.switch_page("pages/p_overview.py")

# ── Shared result header + KPI row (visible on all pages when result exists) ──
result = st.session_state.get("result")
if result:
    sim_cfg  = st.session_state.get("payload", {}).get("config", {})
    n_months = sim_cfg.get("n_months",      cfg["n_months"])
    n_mc     = sim_cfg.get("n_monte_carlo", cfg["n_mc"])
    n_users  = sim_cfg.get("n_users",       cfg["n_users"])
    assum    = result["assumptions"]

    col_hdr, col_act = st.columns([3, 1])
    with col_hdr:
        st.markdown(
            f'<div class="vg-result-title">{result["product_name"]}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="vg-result-sub">'
            f'{n_months}-month forecast &nbsp;·&nbsp; {n_mc} Monte Carlo runs'
            f' &nbsp;·&nbsp; {n_users:,} synthetic users'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_act:
        st.markdown("<br>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔄  Re-run", use_container_width=True):
                st.session_state.pop("result", None)
                st.rerun()
        with b2:
            if st.button("🏠  New", use_container_width=True):
                for k in ["result", "prefill", "prefill_config", "payload"]:
                    st.session_state.pop(k, None)
                st.rerun()
        base_df = pd.DataFrame(result["base_monthly"])
        st.download_button(
            "⬇️  Export CSV", base_df.to_csv(index=False),
            "simulation.csv", "text/csv", use_container_width=True,
        )

    render_kpi_row([
        ("Final MRR",     f"${result['final_mrr']:,.0f}",             "Monthly recurring revenue"),
        ("Projected ARR", f"${result['final_arr']:,.0f}",             "Annualised run rate"),
        ("Peak Adoption", f"{result['peak_adoption_rate']*100:.1f}%", "Of simulated population"),
        ("Monthly Churn", f"{result['final_churn_rate']*100:.1f}%",   "End-of-period churn"),
        ("TAM",           f"{assum['total_addressable_market']:,}",   "Total addressable market"),
    ], is_dark=is_dark)
    st.markdown("<div style='margin:.5rem 0'></div>", unsafe_allow_html=True)

    on_chain = result.get("on_chain")
    if on_chain:
        gated        = on_chain.get("gated", False)
        job_id       = on_chain.get("job_id")
        rpc_ok       = on_chain.get("rpc_reachable", False)
        chain_err    = on_chain.get("chain_error")
        bal_mon      = on_chain.get("balance_mon")
        wallet_addr  = on_chain.get("wallet", "")
        product_hash = on_chain.get("product_hash", "")
        result_hash  = on_chain.get("result_hash", "")
        req_tx       = on_chain.get("request_tx_url")
        anc_tx       = on_chain.get("anchor_tx_url")

        # Status badge config
        if gated and job_id:
            badge_color, badge_text, badge_emoji = "#818cf8", "ANCHORED ON MONAD", "💜"
        elif rpc_ok:
            badge_color, badge_text, badge_emoji = "#34d399", "MONAD CONNECTED", "🟢"
        else:
            badge_color, badge_text, badge_emoji = "#f59e0b", "MONAD FALLBACK", "🟡"

        bal_display = f"{bal_mon:.6f} MON" if bal_mon is not None else "RPC unreachable"

        tx_links = ""
        if req_tx and not req_tx.startswith("anchor_error"):
            tx_links += f'<a href="{req_tx}" target="_blank" style="color:#34d399;text-decoration:none;font-weight:600;">📄 Request Tx ↗</a>&nbsp;&nbsp;'
        if anc_tx and not anc_tx.startswith("anchor_error"):
            tx_links += f'<a href="{anc_tx}" target="_blank" style="color:#34d399;text-decoration:none;font-weight:600;">📄 Anchor Tx ↗</a>&nbsp;&nbsp;'
        if job_id:
            tx_links += f'<a href="{BACKEND}/api/simulate/verify/{job_id}" target="_blank" style="color:#a78bfa;text-decoration:none;font-weight:600;">🔍 Verify Proof ↗</a>'

        setup_hint = ""
        if not gated:
            setup_hint = (
                f'<div style="margin-top:0.75rem;padding:0.6rem 0.9rem;'
                f'background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.25);'
                f'border-radius:6px;font-size:0.8rem;color:#fbbf24;">'
                f'⚙️ <b>Deploy VingelSimGate.sol</b> + set <code>MONAD_PRIVATE_KEY</code> '
                f'&amp; <code>MONAD_SIMGATE_ADDRESS</code> in <code>.env</code> to enable '
                f'full on-chain gating &amp; job anchoring.</div>'
            )

        st.markdown(
            f"""
            <div style="background-color: {'#13141f' if is_dark else '#f3f4f6'}; border: 1px solid {'#2b2d42' if is_dark else '#e5e7eb'}; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.85rem;flex-wrap:wrap;">
                    <span style="font-size:1.2rem;">{badge_emoji}</span>
                    <h4 style="margin:0;color:{badge_color};font-family:'Inter',sans-serif;font-weight:700;">Monad Blockchain Integration</h4>
                    <span style="background:{badge_color}22;border:1px solid {badge_color};color:{badge_color};padding:0.15rem 0.6rem;border-radius:9999px;font-size:0.7rem;font-weight:800;letter-spacing:.08em;">{badge_text}</span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:0.85rem;font-size:0.83rem;font-family:'Inter',sans-serif;">
                    <div>
                        <span style="color:#6b7280;font-weight:600;">Wallet:</span><br>
                        <code style="word-break:break-all;background:{'#252630' if is_dark else '#e5e7eb'};padding:0.2rem 0.4rem;border-radius:4px;color:#34d399;">{wallet_addr}</code>
                    </div>
                    <div>
                        <span style="color:#6b7280;font-weight:600;">MON Balance:</span><br>
                        <span style="color:{'#34d399' if rpc_ok else '#f59e0b'};">{bal_display}</span>
                    </div>
                    <div>
                        <span style="color:#6b7280;font-weight:600;">Product Hash:</span><br>
                        <code style="word-break:break-all;background:{'#252630' if is_dark else '#e5e7eb'};padding:0.2rem 0.4rem;border-radius:4px;color:#9ca3af;">{product_hash[:20]}…</code>
                    </div>
                    <div>
                        <span style="color:#6b7280;font-weight:600;">Result Hash:</span><br>
                        <code style="word-break:break-all;background:{'#252630' if is_dark else '#e5e7eb'};padding:0.2rem 0.4rem;border-radius:4px;color:#9ca3af;">{result_hash[:20]}…</code>
                    </div>
                    {f'<div><span style="color:#6b7280;font-weight:600;">Job ID:</span><br><code style="word-break:break-all;background:{"#252630" if is_dark else "#e5e7eb"};padding:0.2rem 0.4rem;border-radius:4px;color:#f472b6;">{job_id}</code></div>' if job_id else ''}
                </div>
                {f'<div style="margin-top:0.85rem;border-top:1px solid {"#1f202e" if is_dark else "#e5e7eb"};padding-top:0.65rem;display:flex;flex-wrap:wrap;gap:0.75rem;font-size:0.83rem;">{tx_links}</div>' if tx_links else ''}
                {f'<div style="margin-top:0.6rem;font-size:0.78rem;color:#ef4444;">⚠️ Chain error: {chain_err[:100]}</div>' if chain_err else ''}
                {setup_hint}
            </div>
            """,
            unsafe_allow_html=True
        )



pg.run()
