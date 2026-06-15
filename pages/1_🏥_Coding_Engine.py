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

# ── Load demo data ────────────────────────────────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "coding_demo_data.json"

@st.cache_data
def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)

try:
    data = load_data()
except FileNotFoundError:
    st.error("coding_demo_data.json not found at repo root.")
    st.stop()

cases = data.get("cases", [])
if not cases:
    st.error("No cases found in coding_demo_data.json.")
    st.stop()

# Defensive label — fallback to encounter_id if label missing
def case_label(c):
    return c.get("label") or c.get("encounter_id", "Unknown")

label_to_case = {case_label(c): c for c in cases}

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIDENCE_COLORS = {"high": "🟢", "medium": "🟡", "low": "🔴"}
CODE_TYPE_LABELS  = {"primary": "PRIMARY", "secondary": "SECONDARY", "additional": "ADDITIONAL"}

# ── Renderers ────────────────────────────────────────────────────────────────

def render_header():
    st.markdown(
        """
        <div style='background:#1F3864;padding:16px 20px;
                    border-radius:8px;margin-bottom:20px'>
            <h2 style='color:white;margin:0;font-size:1.4rem'>
                🏥 Clinical Coding Assistant
            </h2>
            <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
                AI-powered ICD-10 &amp; CPT suggestion engine
                with prior authorization assessment
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_encounter_header(enc):
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Setting",  enc.get("setting", enc.get("encounter_class", "—")))
    col2.metric("Date",     enc.get("encounter_date", "—"))
    col3.metric("Duration", f"{enc['duration_hours']}h" if enc.get("duration_hours") else "—")
    col4.metric("Gender",   enc.get("patient_gender", "—"))
    col5.metric("Age",      enc.get("patient_age", "—"))
    st.caption(f"**Reason:** {enc.get('reason', 'Not documented')}")

def render_icd10(icd10_suggestions):
    st.markdown("### 📋 ICD-10 Diagnosis Codes")
    if not icd10_suggestions:
        st.warning("No ICD-10 suggestions returned")
        return
    for s in icd10_suggestions:
        conf  = CONFIDENCE_COLORS.get(s["confidence"], "⚪")
        ctype = CODE_TYPE_LABELS.get(s.get("code_type", ""), s.get("code_type", ""))
        with st.expander(f"{conf} **{s['code']}** — {s['description']}  `{ctype}`", expanded=True):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(f"**Confidence:** {s['confidence'].title()}  |  **Code type:** {ctype}")

def render_cpt(cpt_suggestions):
    st.markdown("### 🔧 CPT Procedure Codes")
    if not cpt_suggestions:
        st.warning("No CPT suggestions returned")
        return
    for s in cpt_suggestions:
        conf = CONFIDENCE_COLORS.get(s["confidence"], "⚪")
        with st.expander(f"{conf} **{s['code']}** — {s['description']}", expanded=True):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(f"**Confidence:** {s['confidence'].title()}")

def render_prior_auth(prior_auth):
    st.markdown("### 🔐 Prior Authorization Assessment")
    if not prior_auth:
        return
    required = prior_auth.get("required") or prior_auth.get("encounter_requires_auth", False)
    summary  = prior_auth.get("reason") or prior_auth.get("summary", "")
    if required:
        st.error(f"⚠️ **Authorization required** — {summary}")
    else:
        st.success(f"✅ {summary}")
    supporting = prior_auth.get("supporting_codes", [])
    if supporting:
        st.caption(f"Supporting codes: {', '.join(supporting)}")

def render_medication_review(flag):
    st.markdown("### 💊 Medication Review")
    if not flag:
        return
    if flag.get("flagged"):
        st.warning(f"⚠️ **Review recommended** — {flag['reason']}")
        st.caption(f"**Action:** {flag['action']}")
    else:
        st.success(f"✅ No review required — {flag.get('reason', '')}")

def render_coding_notes(notes):
    if not notes:
        return
    st.markdown("### 📝 Coding Notes")
    for note in notes:
        st.info(f"ℹ️ {note}")

def render_evaluation(evaluation):
    st.markdown("### 📊 Evaluation vs Ground Truth")
    ev = evaluation.get("icd10_evaluation", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precision",    f"{ev.get('concept_precision', 0):.0%}")
    col2.metric("Recall",       f"{ev.get('concept_recall', 0):.0%}")
    col3.metric("Suggested",    ev.get("suggested_count", 0))
    col4.metric("Ground truth", ev.get("ground_truth_count", 0))
    with st.expander("View match details"):
        for m in ev.get("match_details", []):
            icon = "✅" if m["concept_match"] else "❌"
            st.markdown(f"{icon} `{m['suggested_code']}` — {m['suggested_desc']}  _{m['confidence']} confidence_")
    with st.expander("View ground truth conditions"):
        for gt in evaluation.get("ground_truth", {}).get("conditions", []):
            st.markdown(f"- {gt['display']}  `{gt['code']}`")

# ── Main ──────────────────────────────────────────────────────────────────────

render_header()

col_select, col_run, col_spacer = st.columns([3, 1, 2])
with col_select:
    selected_label = st.selectbox(
        "Select encounter",
        options=list(label_to_case.keys()),
        index=0,
        label_visibility="collapsed",
    )
with col_run:
    run_clicked = st.button("▶ Run engine", type="primary", use_container_width=True)

st.divider()

if "coding_result" not in st.session_state:
    st.session_state.coding_result = None

if run_clicked:
    case = label_to_case[selected_label]
    icd_count = len(case["suggestions"].get("icd10_suggestions", []))
    cpt_count = len(case["suggestions"].get("cpt_suggestions", []))
    st.session_state.coding_result = case
    st.success(f"✅ Engine completed — {icd_count} ICD-10 codes, {cpt_count} CPT codes suggested")

if st.session_state.coding_result:
    case = st.session_state.coding_result
    enc  = case["encounter"]
    render_encounter_header(enc)

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("## Clinical Context")
        st.divider()
        st.info("ℹ️ Full clinical context requires a database connection. Run locally with `coding_app.py` for the complete view.")
        st.markdown("#### 🔴 Diagnoses (from ICD-10 suggestions)")
        for s in case["suggestions"].get("icd10_suggestions", []):
            ctype = CODE_TYPE_LABELS.get(s.get("code_type", ""), "")
            conf  = CONFIDENCE_COLORS.get(s["confidence"], "⚪")
            st.markdown(f"- {conf} **{s['description']}** `{s['code']}` _{ctype}_")
        st.divider()
        st.markdown("#### ⚕️ Procedures (from CPT suggestions)")
        for s in case["suggestions"].get("cpt_suggestions", []):
            conf = CONFIDENCE_COLORS.get(s["confidence"], "⚪")
            st.markdown(f"- {conf} {s['description']} `{s['code']}`")
        st.divider()
        st.markdown("#### 📋 Ground Truth (Synthea)")
        for gt in case["evaluation"].get("ground_truth", {}).get("conditions", []):
            st.markdown(f"- {gt['display']}  `{gt['code']}`")

    with right:
        st.markdown("## Coding Suggestions")
        render_icd10(case["suggestions"].get("icd10_suggestions", []))
        st.divider()
        render_cpt(case["suggestions"].get("cpt_suggestions", []))
        st.divider()
        render_prior_auth(case["suggestions"].get("prior_auth_assessment", {}))
        st.divider()
        render_medication_review(case["suggestions"].get("medication_review_flag", {}))
        st.divider()
        render_coding_notes(case["suggestions"].get("coding_notes", []))
        st.divider()
        render_evaluation(case["evaluation"])
else:
    st.markdown(
        """
        <div style='text-align:center;padding:60px;color:#888;font-size:1.1rem'>
            Select an encounter above and click
            <strong>▶ Run engine</strong> to begin
        </div>
        """,
        unsafe_allow_html=True,
    )
