# pages/1_🏥_Coding_Engine.py
import json
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Clinical Coding Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_PATH = Path(__file__).parent.parent / "coding_demo_data.json"

# Cache busted with ttl=0 to always read fresh from disk
@st.cache_data(ttl=0)
def load_coding_data():
    with open(DATA_PATH) as f:
        raw = json.load(f)
    return raw["cases"]

# ── Constants ──────────────────────────────────────────────────────────────────
CONF  = {"high": "🟢", "medium": "🟡", "low": "🔴"}
CTYPE = {"primary": "PRIMARY", "secondary": "SECONDARY", "additional": "ADDITIONAL"}

# ── Renderers ──────────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div style='background:#1F3864;padding:16px 20px;border-radius:8px;margin-bottom:20px'>
        <h2 style='color:white;margin:0;font-size:1.4rem'>🏥 Clinical Coding Assistant</h2>
        <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
            AI-powered ICD-10 &amp; CPT suggestion engine with prior authorization assessment
        </p>
    </div>""", unsafe_allow_html=True)

def render_encounter_header(enc):
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Setting",  enc.get("setting","—"))
    c2.metric("Date",     enc.get("encounter_date","—"))
    c3.metric("Duration", f"{enc['duration_hours']}h" if enc.get("duration_hours") else "—")
    c4.metric("Gender",   enc.get("patient_gender","—"))
    c5.metric("Age",      enc.get("patient_age","—"))
    st.caption(f"**Reason:** {enc.get('reason','Not documented')}")

def render_icd10(items):
    st.markdown("### 📋 ICD-10 Diagnosis Codes")
    if not items: st.warning("No ICD-10 suggestions"); return
    for s in items:
        ct = CTYPE.get(s.get("code_type",""), s.get("code_type",""))
        with st.expander(f"{CONF.get(s['confidence'],'⚪')} **{s['code']}** — {s['description']}  `{ct}`", expanded=True):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(f"**Confidence:** {s['confidence'].title()}  |  **Code type:** {ct}")

def render_cpt(items):
    st.markdown("### 🔧 CPT Procedure Codes")
    if not items: st.warning("No CPT suggestions"); return
    for s in items:
        with st.expander(f"{CONF.get(s['confidence'],'⚪')} **{s['code']}** — {s['description']}", expanded=True):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(f"**Confidence:** {s['confidence'].title()}")

def render_prior_auth(pa):
    st.markdown("### 🔐 Prior Authorization Assessment")
    if not pa:
        return
    req = pa.get("required") or pa.get("encounter_requires_auth", False)
    msg = str(pa.get("reason") or pa.get("summary") or "")
    if req:
        st.error(f"⚠️ **Authorization required** — {msg}")
    else:
        st.success(f"✅ {msg}")
    codes = pa.get("supporting_codes", [])
    if codes:
        st.caption(f"Supporting codes: {', '.join(codes)}")

def render_med_review(flag):
    st.markdown("### 💊 Medication Review")
    if not flag: return
    if flag.get("flagged"):
        st.warning(f"⚠️ **Review recommended** — {flag['reason']}")
        st.caption(f"**Action:** {flag['action']}")
    else:
        st.success(f"✅ No review required — {flag.get('reason','')}")

def render_notes(notes):
    if not notes: return
    st.markdown("### 📝 Coding Notes")
    for n in notes: st.info(f"ℹ️ {n}")

def render_evaluation(ev_block):
    st.markdown("### 📊 Evaluation vs Ground Truth")
    ev = ev_block.get("icd10_evaluation", {})
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Precision",    f"{ev.get('concept_precision',0):.0%}")
    c2.metric("Recall",       f"{ev.get('concept_recall',0):.0%}")
    c3.metric("Suggested",    ev.get("suggested_count",0))
    c4.metric("Ground truth", ev.get("ground_truth_count",0))
    with st.expander("View match details"):
        for m in ev.get("match_details",[]):
            icon = "✅" if m["concept_match"] else "❌"
            st.markdown(f"{icon} `{m['suggested_code']}` — {m['suggested_desc']}  _{m['confidence']}_")
    with st.expander("View ground truth conditions"):
        for gt in ev_block.get("ground_truth",{}).get("conditions",[]):
            st.markdown(f"- {gt['display']}  `{gt['code']}`")

# ── Main ───────────────────────────────────────────────────────────────────────
render_header()

cases = load_coding_data()
labels = [c["label"] for c in cases]
label_map = {c["label"]: c for c in cases}

col_sel, col_btn, col_sp = st.columns([3,1,2])
with col_sel:
    selected_label = st.selectbox("Select encounter", labels, index=0, label_visibility="collapsed")
with col_btn:
    run = st.button("▶ Run engine", type="primary", use_container_width=True)

st.divider()

if "coding_case" not in st.session_state:
    st.session_state.coding_case = None

if run:
    st.session_state.coding_case = label_map[selected_label]

case = st.session_state.coding_case

if case:
    enc  = case["encounter"]
    sugg = case["suggestions"]
    ev   = case["evaluation"]

    icd_n = len(sugg.get("icd10_suggestions",[]))
    cpt_n = len(sugg.get("cpt_suggestions",[]))
    st.success(f"✅ Engine completed — {icd_n} ICD-10 codes, {cpt_n} CPT codes suggested")

    render_encounter_header(enc)
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("## Clinical Context")
        st.divider()
        st.info("ℹ️ Full clinical context requires DB. Run `coding_app.py` locally for the complete view.")
        st.markdown("#### 🔴 Diagnoses")
        for s in sugg.get("icd10_suggestions",[]):
            st.markdown(f"- {CONF.get(s['confidence'],'⚪')} **{s['description']}** `{s['code']}` _{CTYPE.get(s.get('code_type',''),'')}_")
        st.divider()
        st.markdown("#### ⚕️ Procedures")
        for s in sugg.get("cpt_suggestions",[]):
            st.markdown(f"- {CONF.get(s['confidence'],'⚪')} {s['description']} `{s['code']}`")
        st.divider()
        st.markdown("#### 📋 Ground Truth (Synthea)")
        for gt in ev.get("ground_truth",{}).get("conditions",[]):
            st.markdown(f"- {gt['display']}  `{gt['code']}`")

    with right:
        st.markdown("## Coding Suggestions")
        render_icd10(sugg.get("icd10_suggestions",[]))
        st.divider()
        render_cpt(sugg.get("cpt_suggestions",[]))
        st.divider()
        render_prior_auth(sugg.get("prior_auth_assessment",{}))
        st.divider()
        render_med_review(sugg.get("medication_review_flag",{}))
        st.divider()
        render_notes(sugg.get("coding_notes",[]))
        st.divider()
        render_evaluation(ev)
else:
    st.markdown("""
    <div style='text-align:center;padding:60px;color:#888;font-size:1.1rem'>
        Select an encounter above and click <strong>▶ Run engine</strong> to begin
    </div>""", unsafe_allow_html=True)
