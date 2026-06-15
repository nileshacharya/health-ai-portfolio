# Home.py — Healthcare AI Portfolio Landing Page

import streamlit as st

st.set_page_config(
    page_title="Healthcare AI Portfolio — Nilesh Acharya",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='background:#1F3864;padding:20px 24px;border-radius:8px;margin-bottom:24px'>
        <h1 style='color:white;margin:0;font-size:1.8rem'>🏥 Healthcare AI Portfolio</h1>
        <p style='color:#A8C8E8;margin:6px 0 0 0;font-size:0.95rem'>
            Nilesh Acharya — AI Product Manager
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Bio ───────────────────────────────────────────────────────────────────────
st.markdown("## About")
st.markdown(
    """
    9+ years in product management, 17+ years working alongside engineering teams across
    healthcare technology, data platforms, and enterprise software.
    Deep focus on clinical AI — revenue cycle, documentation automation, and care coordination workflows.

    This portfolio demonstrates AI PM thinking end-to-end: problem sizing, system design,
    working prototypes, and evaluation frameworks — not just slide decks.
    """
)

col_gh, col_yt = st.columns([1, 5])
with col_gh:
    st.link_button("GitHub", "https://github.com/nileshacharya/health-ai-portfolio")
with col_yt:
    st.link_button("▶ Demo Video", "https://youtu.be/H5mB_1b4DD8")

st.divider()

# ── Project Table ─────────────────────────────────────────────────────────────
st.markdown("## Projects")

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown(
        """
        <div style='border:1px solid #e2e8f0;border-radius:8px;padding:20px;height:100%'>
            <div style='font-size:2rem'>🏥</div>
            <h3 style='margin:8px 0 4px 0'>Clinical Coding Assistant</h3>
            <p style='color:#475569;font-size:0.85rem;margin:0 0 12px 0'>Project 1</p>
            <p>AI-powered ICD-10 & CPT suggestion engine with prior authorization assessment.
            Reduces coding errors and missed revenue in clinical encounters.</p>
            <br>
            <b>Problem:</b> Clinicians under-code or mis-code encounters → lost revenue<br>
            <b>Output:</b> ICD-10 + CPT recommendations with confidence scores<br>
            <b>Data:</b> Synthea synthetic EHR (FHIR)<br>
            <b>Model:</b> Claude API
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div style='border:1px solid #e2e8f0;border-radius:8px;padding:20px;height:100%'>
            <div style='font-size:2rem'>🩺</div>
            <h3 style='margin:8px 0 4px 0'>Ambient Documentation</h3>
            <p style='color:#475569;font-size:0.85rem;margin:0 0 12px 0'>Project 2</p>
            <p>Converts patient-clinician conversations into structured SOAP notes
            with source attribution and hallucination detection.</p>
            <br>
            <b>Problem:</b> Clinicians spend >50% of visit time on notes → burnout<br>
            <b>Output:</b> SOAP notes with per-claim source attribution<br>
            <b>Data:</b> MTSamples (General Medicine, 259 cases)<br>
            <b>Model:</b> Claude API
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div style='border:1px solid #e2e8f0;border-radius:8px;padding:20px;height:100%'>
            <div style='font-size:2rem'>🤝</div>
            <h3 style='margin:8px 0 4px 0'>Warm Handoff</h3>
            <p style='color:#475569;font-size:0.85rem;margin:0 0 12px 0'>Project 3</p>
            <p>AI support triage that silently monitors bot-customer conversations
            and fires escalation with a structured brief to the human agent — no context lost.</p>
            <br>
            <b>Problem:</b> Bot-to-human escalations lose context → frustrated customers<br>
            <b>Output:</b> Escalation handoff card with issue summary + steps tried<br>
            <b>Stack:</b> HTML/JS + Claude API (browser-side)<br>
            <b>Model:</b> Claude API
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ── Clinical AI Arc ───────────────────────────────────────────────────────────
st.markdown("## The Clinical AI Value Chain")
st.markdown(
    "Projects 1 and 2 cover the full clinical documentation-to-billing pipeline:"
)

st.markdown(
    """
    <div style='display:flex;align-items:center;gap:12px;padding:16px;
                background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0'>
        <div style='text-align:center;flex:1'>
            <div style='font-size:1.5rem'>🩺</div>
            <div style='font-weight:600'>Encounter</div>
            <div style='font-size:0.8rem;color:#475569'>Patient visit</div>
        </div>
        <div style='font-size:1.5rem;color:#94a3b8'>→</div>
        <div style='text-align:center;flex:1'>
            <div style='font-size:1.5rem'>📄</div>
            <div style='font-weight:600'>Documentation</div>
            <div style='font-size:0.8rem;color:#475569'>Project 2: SOAP note generation</div>
        </div>
        <div style='font-size:1.5rem;color:#94a3b8'>→</div>
        <div style='text-align:center;flex:1'>
            <div style='font-size:1.5rem'>💰</div>
            <div style='font-weight:600'>Billing</div>
            <div style='font-size:0.8rem;color:#475569'>Project 1: ICD-10 + CPT coding</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()
st.caption(
    "Built by Nilesh Acharya · "
    "[GitHub](https://github.com/nileshacharya/health-ai-portfolio) · "
    "No real patient data used in any project"
)
