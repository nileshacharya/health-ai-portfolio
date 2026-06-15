# pages/2_🩺_Ambient_Docs.py
import json
import os
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Ambient Documentation",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Load demo data ────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "demo_data.json"

@st.cache_data
def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='background:#1F3864;padding:16px 20px;
                border-radius:8px;margin-bottom:20px'>
        <h2 style='color:white;margin:0;font-size:1.4rem'>
            🩺 Ambient Documentation
        </h2>
        <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
            AI-powered SOAP note generation with source attribution
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Mode toggle ───────────────────────────────────────────────────────────────
mode = st.radio(
    "Mode",
    ["📋 Demo Mode", "⚡ Live Mode"],
    horizontal=True,
    help="Demo: instant pre-generated results — no API key needed. Live: real-time via Claude API.",
)
st.divider()

# ── Shared display ────────────────────────────────────────────────────────────
def show_metrics(stats):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Entities",  stats["total_entities"])
    col2.metric("Hallucinations",  stats["hallucination_count"])
    col3.metric("Coverage",        f"{stats['attribution_coverage']:.1%}")
    col4.metric("Quality",         stats["quality_score"].upper())

def show_results(conversation, soap_note, attributions):
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Conversation")
        st.text(conversation)
    with col_right:
        tab_soap, tab_attr = st.tabs(["SOAP Note", "Attributions"])
        with tab_soap:
            st.text(soap_note)
        with tab_attr:
            found    = [a for a in attributions if not a["is_hallucination"]]
            hallucin = [a for a in attributions if a["is_hallucination"]]
            st.caption(f"✅ {len(found)} attributed   ⚠️ {len(hallucin)} not found in source")
            st.divider()
            for attr in attributions:
                icon   = "⚠️" if attr["is_hallucination"] else "✅"
                source = attr.get("source_text") or "not found in conversation"
                st.write(f"{icon} **{attr['soap_text']}** → {source}")

# ── DEMO MODE ─────────────────────────────────────────────────────────────────
if mode == "📋 Demo Mode":
    try:
        demo_data = load_data()
    except FileNotFoundError:
        st.error("demo_data.json not found at repo root.")
        st.stop()

    cases = demo_data.get("cases", [])
    if not cases:
        st.error("No cases found in demo_data.json.")
        st.stop()

    # Defensive label — fallback chain if expected keys missing
    def case_label(c):
        name = c.get("sample_name") or c.get("id") or c.get("conversation_id", "Unknown")
        cat  = c.get("category", "")
        return f"{name}  [{cat}]" if cat else name

    options = {case_label(c): c for c in cases}

    selected_label = st.selectbox(
        "Medical Sample",
        list(options.keys()),
        index=min(2, len(options) - 1),
    )
    selected = options[selected_label]
    st.caption(selected.get("description", ""))
    st.success("✓ Pre-generated results loaded")

    # Defensive stats access
    stats = selected.get("statistics")
    if not stats:
        st.error("Statistics missing from this case. Please re-generate demo_data.json.")
        st.stop()

    show_metrics(stats)
    st.divider()
    show_results(
        selected.get("conversation", ""),
        selected.get("soap_note", ""),
        selected.get("attributions", [])
    )

# ── LIVE MODE ─────────────────────────────────────────────────────────────────
else:
    st.info(
        "⚡ **Live Mode** requires a local setup with `ANTHROPIC_API_KEY` configured. "
        "Use **Demo Mode** to explore pre-generated results without any setup."
    )
