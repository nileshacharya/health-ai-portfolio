# pages/3_🤝_Warm_Handoff.py
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="Warm Handoff",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='background:#1F3864;padding:16px 20px;
                border-radius:8px;margin-bottom:20px'>
        <h2 style='color:white;margin:0;font-size:1.4rem'>
            🤝 Warm Handoff
        </h2>
        <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
            AI support triage — silent monitoring, smart escalation, zero context lost
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── How it works ──────────────────────────────────────────────────────────────
with st.expander("ℹ️ How it works", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**1. Bot handles the conversation**")
        st.markdown("Ganu (the support bot) resolves common issues autonomously.")
    with col2:
        st.markdown("**2. Evaluator watches silently**")
        st.markdown(
            "After every turn, a second AI evaluates sentiment, frustration, "
            "and escalation confidence — invisibly."
        )
    with col3:
        st.markdown("**3. Handoff fires with full context**")
        st.markdown(
            "When escalation threshold is met, the human agent receives a "
            "structured brief: issue summary, steps tried, sentiment, urgency, recommended first action."
        )

st.caption("⚠️ Requires your own Anthropic API key — enter it in the app below.")
st.divider()

# ── Embed the HTML app ────────────────────────────────────────────────────────
HTML_PATH = Path(__file__).parent.parent / "ganu.html"

with open(HTML_PATH, "r") as f:
    html_content = f.read()

components.html(html_content, height=750, scrolling=False)
