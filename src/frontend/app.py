import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000"
API_KEY = "drhp-secret-key-2024"
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(
    page_title="IPO DRHP Intelligence Agent",
    page_icon="📊",
    layout="wide"
)

st.title("📊 IPO DRHP Intelligence Agent")
st.caption("AI-powered Indian IPO analysis using LangGraph multi-agent system")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.write("Upload any Indian IPO DRHP PDF and get an instant analysis with BUY/AVOID/WATCH verdict.")
    st.divider()
    st.warning("⚠️ This is educational analysis only. NOT investment advice.")
    st.divider()
    st.header("🔍 What we analyze")
    st.write("✅ Red Flags Detection")
    st.write("✅ Financial Health Score")
    st.write("✅ Promoter Background Check")
    st.write("✅ Valuation Assessment")
    st.write("✅ Final BUY/AVOID/WATCH Verdict")

# File Upload
st.header("📁 Upload DRHP PDF")
uploaded_file = st.file_uploader(
    "Drag and drop your DRHP PDF here",
    type=["pdf"],
    help="Maximum file size: 50MB"
)

if uploaded_file:
    st.success(f"✅ File uploaded: {uploaded_file.name} ({round(uploaded_file.size/1024/1024, 1)} MB)")

    if st.button("🚀 Start Analysis", type="primary"):
        with st.spinner("Submitting to API..."):
            try:
                response = requests.post(
                    f"{API_URL}/analyze",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    headers=HEADERS  # API key sent here
                )
                if response.status_code == 200:
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    st.session_state["job_id"] = job_id
                    st.success(f"Analysis started! Job ID: {job_id}")
                elif response.status_code == 403:
                    st.error("API key invalid. Check your configuration.")
                else:
                    st.error(f"API error: {response.text}")
            except Exception as e:
                st.error(f"Could not connect to API: {e}")

# Progress Tracker
if "job_id" in st.session_state:
    job_id = st.session_state["job_id"]

    status_messages = {
        "queued": "⏳ Queued...",
        "loading_pdf": "📄 Loading and extracting PDF...",
        "embedding": "🔢 Embedding chunks into ChromaDB...",
        "analyzing": "🤖 Running 6 AI agents...",
        "complete": "✅ Analysis complete!",
        "failed": "❌ Analysis failed"
    }

    if "report_data" not in st.session_state:
        progress_bar = st.progress(0)
        status_text = st.empty()

        progress_map = {
            "queued": 5,
            "loading_pdf": 20,
            "embedding": 40,
            "analyzing": 70,
            "complete": 100,
            "failed": 0
        }

        while True:
            try:
                # Status endpoint — no auth needed
                status_resp = requests.get(f"{API_URL}/status/{job_id}")
                status_data = status_resp.json()
                current_status = status_data["status"]

                progress_bar.progress(progress_map.get(current_status, 0))
                status_text.info(status_messages.get(current_status, current_status))

                if current_status == "complete":
                    # Report endpoint — needs auth
                    report_resp = requests.get(
                        f"{API_URL}/report/{job_id}",
                        headers=HEADERS  # API key sent here
                    )
                    st.session_state["report_data"] = report_resp.json()
                    st.rerun()
                    break
                elif current_status == "failed":
                    st.error(f"Analysis failed: {status_data['message']}")
                    break

                time.sleep(3)
            except Exception as e:
                st.error(f"Error polling status: {e}")
                break

# Display Report
if "report_data" in st.session_state:
    data = st.session_state["report_data"]

    st.divider()

    # Verdict Banner
    verdict = data.get("verdict", "WATCH")
    verdict_colors = {"BUY": "🟢", "AVOID": "🔴", "WATCH": "🟡"}
    verdict_icon = verdict_colors.get(verdict, "🟡")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Verdict", f"{verdict_icon} {verdict}")
    with col2:
        st.metric("Risk Score", f"{data.get('risk_score', 0)}/10")
    with col3:
        st.metric("Financial Health", f"{data.get('financial_health_score', 0)}/10")
    with col4:
        valuation = data.get("valuation", {}).get("valuation_call", "N/A")
        st.metric("Valuation", valuation)

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Full Report",
        "🚨 Red Flags",
        "💰 Financials",
        "👤 Promoters",
        "📈 Valuation"
    ])

    with tab1:
        st.markdown(data.get("final_report", ""))

    with tab2:
        red_flags = data.get("red_flags", [])
        st.subheader(f"Total Red Flags: {len(red_flags)}")

        severity_colors = {
            "CRITICAL": "🔴",
            "MODERATE": "🟠",
            "MINOR": "🟡"
        }

        for flag in red_flags:
            severity = flag.get("severity", "MINOR")
            icon = severity_colors.get(severity, "🟡")
            with st.expander(f"{icon} [{severity}] {flag.get('flag', '')}"):
                st.write("**Plain English:**", flag.get("plain_english", ""))
                if flag.get("source_quote"):
                    st.caption(f"📄 Source: {flag.get('source_quote', '')[:200]}")

    with tab3:
        financials = data.get("financials", {})
        extracted = financials.get("extracted", {})
        ratios = financials.get("ratios", {})
        fy24 = extracted.get("fy2024", {})

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("FY2024 Key Numbers")
            st.metric("Revenue", f"₹{fy24.get('revenue', 'N/A')} million")
            st.metric("PAT", f"₹{fy24.get('pat', 'N/A')} million")
            st.metric("Total Debt", f"₹{fy24.get('total_debt', 'N/A')} million")

        with col2:
            st.subheader("Key Ratios")
            st.metric("Revenue CAGR", f"{ratios.get('revenue_cagr', 'N/A')}%")
            st.metric("PAT Margin", f"{ratios.get('pat_margin_fy24', 'N/A')}%")
            st.metric("Debt/Equity", ratios.get('debt_to_equity', 'N/A'))
            st.metric("Current Ratio", ratios.get('current_ratio', 'N/A'))

        # Revenue chart
        try:
            import plotly.graph_objects as go
            fy22_rev = extracted.get("fy2022", {}).get("revenue")
            fy23_rev = extracted.get("fy2023", {}).get("revenue")
            fy24_rev = extracted.get("fy2024", {}).get("revenue")

            if all([fy22_rev, fy23_rev, fy24_rev]):
                fig = go.Figure(data=[
                    go.Bar(
                        x=["FY2022", "FY2023", "FY2024"],
                        y=[fy22_rev, fy23_rev, fy24_rev],
                        marker_color=["#636EFA", "#636EFA", "#00CC96"]
                    )
                ])
                fig.update_layout(
                    title="Revenue Trend (₹ Million)",
                    xaxis_title="Year",
                    yaxis_title="Revenue"
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

    with tab4:
        promoters = data.get("promoter_report", [])
        rating_colors = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}

        for p in promoters:
            rating = p.get("rating", "YELLOW")
            icon = rating_colors.get(rating, "🟡")
            with st.expander(f"{icon} {p.get('name', '')} — {rating}"):
                st.write(p.get("key_findings", ""))
                concerns = p.get("concerns", [])
                if concerns:
                    st.write("**Concerns:**")
                    for c in concerns:
                        st.write(f"• {c}")

    with tab5:
        valuation = data.get("valuation", {})
        st.subheader(f"Valuation: {valuation.get('valuation_call', 'N/A')}")
        st.write("**Reasoning:**", valuation.get("reasoning", ""))

        if valuation.get("sector_avg_pe"):
            st.metric("Sector Avg P/E", valuation.get("sector_avg_pe"))
        if valuation.get("issue_pe"):
            st.metric("Issue P/E", valuation.get("issue_pe"))
        if valuation.get("is_loss_making"):
            st.info("ℹ️ Company is loss-making — P/E ratio not applicable")

        peers = valuation.get("peer_companies", [])
        if peers:
            st.write("**Peer Companies:**", ", ".join(peers))

    # Download report
    st.divider()
    st.download_button(
        label="📥 Download Full Report",
        data=data.get("final_report", ""),
        file_name=f"{data.get('company', 'report')}_analysis.txt",
        mime="text/plain"
    )

    if st.button("🔄 Analyze Another DRHP"):
        del st.session_state["job_id"]
        del st.session_state["report_data"]
        st.rerun()