# pages/2_🩺_Ambient_Docs.py
import json
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Ambient Documentation",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_PATH = Path(__file__).parent.parent / "demo_data.json"

@st.cache_data(ttl=0)
def load_ambient_data():
    with open(DATA_PATH) as f:
        raw = json.load(f)
    return raw["cases"]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:#1F3864;padding:16px 20px;border-radius:8px;margin-bottom:20px'>
    <h2 style='color:white;margin:0;font-size:1.4rem'>🩺 Ambient Documentation</h2>
    <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
        AI-powered SOAP note generation with source attribution
    </p>
</div>""", unsafe_allow_html=True)

mode = st.radio("Mode", ["📋 Demo Mode", "⚡ Live Mode"], horizontal=True)
st.divider()

def show_metrics(stats):
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Entities",  stats["total_entities"])
    c2.metric("Hallucinations",  stats["hallucination_count"])
    c3.metric("Coverage",        f"{stats['attribution_coverage']:.1%}")
    c4.metric("Quality",         stats["quality_score"].upper())

def show_results(conversation, soap_note, attributions):
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Conversation")
        st.text(conversation)
    with col_r:
        tab_soap, tab_attr = st.tabs(["SOAP Note", "Attributions"])
        with tab_soap:
            st.text(soap_note)
        with tab_attr:
            found   = [a for a in attributions if not a["is_hallucination"]]
            hallucs = [a for a in attributions if a["is_hallucination"]]
            st.caption(f"✅ {len(found)} attributed   ⚠️ {len(hallucs)} not found in source")
            st.divider()
            for attr in attributions:
                icon   = "⚠️" if attr["is_hallucination"] else "✅"
                source = attr.get("source_text") or "not found in conversation"
                st.write(f"{icon} **{attr['soap_text']}** → {source}")

if mode == "📋 Demo Mode":
    cases = load_ambient_data()
    labels = [f"{c['sample_name']}  [{c['category']}]" for c in cases]
    label_map = {f"{c['sample_name']}  [{c['category']}]": c for c in cases}

    selected_label = st.selectbox("Medical Sample", labels, index=2)
    selected = label_map[selected_label]
    st.caption(selected.get("description",""))
    st.success("✓ Pre-generated results loaded")
    show_metrics(selected["statistics"])
    st.divider()
    show_results(selected["conversation"], selected["soap_note"], selected["attributions"])

else:
    st.info(
        "⚡ **Live Mode** requires local setup with `ANTHROPIC_API_KEY`. "
        "Use **Demo Mode** to explore pre-generated results without any setup."
    )
