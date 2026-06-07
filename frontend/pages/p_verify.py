import streamlit as st
import requests
from datetime import datetime

BACKEND = "http://localhost:8000"

st.markdown('<div class="vg-section-head">🔍 On-Chain Proof Verification</div>', unsafe_allow_html=True)
st.write(
    "Verify the authenticity of VINGEL Market Simulator results. "
    "Every gated simulation run checks user MON balance and anchors the final result hash on the Monad Blockchain."
)

# ── Verification Forms ────────────────────────────────────────────────────────
is_dark = st.session_state.get("theme", "dark") == "dark"

with st.container():
    st.markdown(
        f"""
        <div style="background-color: {'#11131e' if is_dark else '#f9fafb'}; border: 1px solid {'#1f2937' if is_dark else '#e5e7eb'}; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
            <h4 style="margin-top: 0; color: #818cf8;">Verify job via Monad SimGate</h4>
            <p style="font-size: 0.85rem; color: #9ca3af; margin-bottom: 1.25rem;">
                Enter a Job ID to retrieve its on-chain status, request timestamp, and anchored result fingerprint. 
                Optionally provide a result hash to verify if the output content is genuine and untampered.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        job_id = st.text_input(
            "Job ID (bytes32 Hex)", 
            placeholder="0x...", 
            value=st.session_state.get("last_job_id", "")
        )
    with col2:
        result_hash = st.text_input(
            "Expected Result Hash (Optional)", 
            placeholder="0x..."
        )

    verify_btn = st.button("Check Monad Proof →", type="primary", use_container_width=True)

if verify_btn:
    if not job_id.strip():
        st.error("Please enter a valid Job ID.")
    else:
        st.session_state["last_job_id"] = job_id.strip()
        with st.spinner("Querying VingelSimGate smart contract on Monad..."):
            try:
                params = {}
                if result_hash.strip():
                    params["result_hash"] = result_hash.strip()
                
                resp = requests.get(f"{BACKEND}/api/simulate/verify/{job_id.strip()}", params=params)
                
                if resp.status_code == 404:
                    st.error(f"Job not found on-chain: {job_id.strip()}")
                else:
                    resp.raise_for_status()
                    job = resp.json()
                    
                    st.success("Proof retrieved from Monad Testnet!")
                    
                    # ── Status Badge ──────────────────────────────────────────
                    status_lbl = "COMPLETED" if job.get("completed") else "PENDING"
                    status_color = "#10b981" if job.get("completed") else "#f59e0b"
                    
                    st.markdown(
                        f"""
                        <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem;">
                            <div style="background-color: {status_color}22; border: 1px solid {status_color}; color: {status_color}; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">
                                {status_lbl}
                            </div>
                            <span style="font-size: 0.85rem; color: #9ca3af;">Anchored on Monad Testnet</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # ── Verification Result Alert ─────────────────────────────
                    if "verification" in job:
                        v = job["verification"]
                        if v.get("matches"):
                            match_time = ""
                            if v.get("stored_at"):
                                dt = datetime.fromtimestamp(v["stored_at"])
                                match_time = f" on {dt.strftime('%b %d, %Y at %I:%M:%S %p')}"
                            
                            st.markdown(
                                f"""
                                <div style="background-color: #04785722; border: 1px solid #059669; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; display: flex; gap: 0.75rem; align-items: flex-start;">
                                    <span style="font-size: 1.25rem;">✅</span>
                                    <div>
                                        <h5 style="margin: 0 0 0.25rem 0; color: #34d399;">Result Authenticated Successfully!</h5>
                                        <p style="margin: 0; font-size: 0.85rem; color: #a7f3d0;">
                                            The provided result hash matches the on-chain proof anchored by the VINGEL backend{match_time}. 
                                            This simulation dataset is verified genuine.
                                        </p>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                """
                                <div style="background-color: #b91c1c22; border: 1px solid #dc2626; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; display: flex; gap: 0.75rem; align-items: flex-start;">
                                    <span style="font-size: 1.25rem;">❌</span>
                                    <div>
                                        <h5 style="margin: 0 0 0.25rem 0; color: #f87171;">Verification Mismatch</h5>
                                        <p style="margin: 0; font-size: 0.85rem; color: #fca5a5;">
                                            The provided result hash does NOT match the anchored value for this Job ID. 
                                            The data may have been modified or belongs to a different simulation.
                                        </p>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    # ── Main Proof Panel ──────────────────────────────────────
                    req_time = "Unknown"
                    comp_time = "Pending"
                    if job.get("requested_at"):
                        req_time = datetime.fromtimestamp(job["requested_at"]).strftime('%Y-%m-%d %H:%M:%S UTC')
                    if job.get("completed_at"):
                        comp_time = datetime.fromtimestamp(job["completed_at"]).strftime('%Y-%m-%d %H:%M:%S UTC')

                    st.markdown(
                        f"""
                        <div style="background-color: {'#171923' if is_dark else '#f3f4f6'}; border: 1px solid {'#2a2c3d' if is_dark else '#e5e7eb'}; padding: 1.25rem; border-radius: 8px; font-family: 'Inter', sans-serif;">
                            <h4 style="margin: 0 0 1rem 0; font-size: 1rem; color: #818cf8;">Smart Contract Data</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; font-size: 0.85rem;">
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Job ID</div>
                                    <code style="word-break: break-all; background: {'#252630' if is_dark else '#e5e7eb'}; padding: 0.2rem; border-radius: 4px;">{job['job_id']}</code>
                                </div>
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Requester Wallet</div>
                                    <code style="word-break: break-all; background: {'#252630' if is_dark else '#e5e7eb'}; padding: 0.2rem; border-radius: 4px;">{job['user']}</code>
                                </div>
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Product Fingerprint (Hash)</div>
                                    <code style="word-break: break-all; background: {'#252630' if is_dark else '#e5e7eb'}; padding: 0.2rem; border-radius: 4px;">{job['product_hash']}</code>
                                </div>
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Anchored Result Hash</div>
                                    <code style="word-break: break-all; background: {'#252630' if is_dark else '#e5e7eb'}; padding: 0.2rem; border-radius: 4px;">{job.get('result_hash') or 'None'}</code>
                                </div>
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Simulation Requested At</div>
                                    <div style="padding-top: 0.25rem;">📅 {req_time}</div>
                                </div>
                                <div>
                                    <div style="color: #6b7280; font-weight: 600;">Result Anchored At</div>
                                    <div style="padding-top: 0.25rem;">📅 {comp_time}</div>
                                </div>
                            </div>
                            <div style="margin-top: 1.25rem; border-top: 1px solid {'#2a2c3d' if is_dark else '#e5e7eb'}; padding-top: 0.75rem; display: flex; gap: 1rem; font-size: 0.85rem;">
                                <a href="https://testnet.monadexplorer.com/address/{job['user']}" target="_blank" style="color: #34d399; text-decoration: none;">📄 View Requester in Explorer ↗</a>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            except Exception as e:
                st.error(f"Error querying backend or blockchain RPC: {e}")
