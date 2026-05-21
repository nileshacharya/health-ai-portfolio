#Changed     header moved out of the two columns

import sys
import json
from pathlib import Path
import streamlit as st

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent.parent))
from coding_engine import (
    build_encounter_context,
    suggest_codes,
    evaluate_suggestions,
)

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Coding Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── evaluation encounters ─────────────────────────────────────────────────────
EVALUATION_ENCOUNTERS = {
    "COVID-19 Isolation — Female 28, Inpatient (Anthem)":
        "9917e9f0-753a-4673-da3f-ca0de161db03",
    "COVID-19 Isolation — Inpatient (Medicaid)":
        "dcbb1003-d8e9-765a-3b63-31305c2a99fe",
    "Renal Transplant — Inpatient (self-pay)":
        "dc267ebd-eaef-eb60-8ac0-c09fc4083f30",
    "CABG History — Inpatient 1981 (self-pay)":
        "78068a3a-2b8c-f9bc-ce77-abb09f0e9fee",
    "CABG History — Inpatient 2023 (self-pay)":
        "53beb3a8-f127-5329-4026-de1cc62ac908",
    "CABG History — Inpatient 2018 (self-pay)":
        "38fc3405-cc74-0d6b-5409-659f0af674f5",
    "CABG History — Inpatient 2021 (self-pay)":
        "af00c0f2-6af8-ea2e-c487-c9f36f89a943",
    "Anemia & Toxoplasmosis — Ambulatory 1991":
        "4c5ae2f5-7f9f-19ae-8c5b-0ce06c9f529c",
    "Diabetic CKD — General Exam Ambulatory 2023":
        "51716af3-8671-a19b-ed20-3006e887392d",
    "Gingivitis & Stress — Check-up Ambulatory 2018":
        "633d2472-8519-8a45-5473-23758e741f0f",
    "Diabetic CKD — Urgent Care Ambulatory 1998":
        "ab585563-a667-be77-37b0-e36396b22486",
    "Stress & SDOH — Check-up Ambulatory 1992":
        "fcdec534-36f9-6899-77c9-1fe0eb549f50",
}

CONFIDENCE_COLORS = {
    "high":   "🟢",
    "medium": "🟡",
    "low":    "🔴",
}

CODE_TYPE_LABELS = {
    "primary":    "PRIMARY",
    "secondary":  "SECONDARY",
    "additional": "ADDITIONAL",
}

# ── helper renderers ──────────────────────────────────────────────────────────

def render_header():
    st.markdown(
        """
        <div style='background:#1F3864;padding:16px 20px;
                    border-radius:8px;margin-bottom:20px'>
            <h2 style='color:white;margin:0;font-size:1.4rem'>
                🏥 Clinical Coding Assistant
            </h2>
            <p style='color:#A8C8E8;margin:4px 0 0 0;font-size:0.85rem'>
                AI-powered ICD-10 & CPT suggestion engine
                with prior authorization assessment
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_encounter_header(enc):
    setting = (
        "Inpatient"    if enc['encounter_class'] == 'IMP'  else
        "Ambulatory"   if enc['encounter_class'] == 'AMB'  else
        "Emergency"    if enc['encounter_class'] == 'EMER' else
        "Home Health"  if enc['encounter_class'] == 'HH'   else
        enc['encounter_class']
    )
    
    # Full-width metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Setting",  setting)
    col2.metric("Date",     enc['encounter_date'])
    col3.metric("Duration", f"{enc['duration_hours']}h"
                            if enc['duration_hours'] else "—")
    col4.metric("Gender",   enc['patient_gender'].title())
    col5.metric("Age",      enc['patient_age'])
    
    st.caption(f"**Reason:** {enc['reason'] or 'Not documented'}")


def render_conditions(conditions):
    st.markdown("#### 🔴 Diagnoses")
    if conditions['diagnoses']:
        for d in conditions['diagnoses']:
            st.markdown(
                f"- **{d['display']}**  "
                f"`{d['code']}` _{d['status']}_"
            )
    else:
        st.caption("No diagnoses documented")

    if conditions['social_determinants']:
        st.markdown("#### 🟡 Social Determinants (Z-code candidates)")
        for s in conditions['social_determinants']:
            st.markdown(f"- {s['display']}")

def render_procedures(procedures):
    st.markdown("#### ⚕️ Procedures")
    if procedures['clinical_procedures']:
        for p in procedures['clinical_procedures']:
            count = p.get('occurrence_count', 1)
            suffix = f" ×{count}" if count > 1 else ""
            st.markdown(
                f"- {p['display']}{suffix}  "
                f"`{p['code']}`"
            )
    else:
        st.caption("No clinical procedures documented")

def render_medications(medications):
    st.markdown("#### 💊 Medications")
    if medications['medications']:
        for m in medications['medications']:
            count = m.get('occurrence_count', 1)
            suffix = f" ×{count}" if count > 1 else ""
            st.markdown(
                f"- {m['display']}{suffix}  "
                f"`RxNorm {m['code']}`"
            )
    else:
        st.caption("No medications documented")

def render_observations(observations):
    st.markdown("#### 🔬 Key Observations")
    if observations['observations']:
        for o in observations['observations'][:10]:
            st.markdown(f"- **{o['display']}:** {o['value']}")
    else:
        st.caption("No observations documented")

def render_insurance(insurance):
    st.markdown("#### 💳 Insurance")
    col1, col2 = st.columns(2)
    col1.markdown(f"**Insurer:** {insurance['insurer']}")
    # With this — derive payer type from insurer name:
    from coding_engine import get_payer_type
    payer_type = get_payer_type(insurance['insurer'])
    col2.markdown(f"**Payer type:** {payer_type.title()}")

    if insurance['total_cost']:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total cost",
                  f"${insurance['total_cost']:,.0f}")
        c2.metric("Insurance paid",
                  f"${insurance['insurance_paid']:,.0f}")
        c3.metric("Patient responsibility",
                  f"${insurance['patient_responsibility']:,.0f}")

    auth_flag = insurance.get('requires_prior_auth', False)
    if auth_flag:
        st.warning("⚠️ Prior auth likely required based on cost threshold")
    else:
        st.success("✅ Below prior auth cost threshold")

def render_icd10(icd10_suggestions):
    st.markdown("### 📋 ICD-10 Diagnosis Codes")
    if not icd10_suggestions:
        st.warning("No ICD-10 suggestions returned")
        return

    for s in icd10_suggestions:
        conf  = CONFIDENCE_COLORS.get(s['confidence'], "⚪")
        ctype = CODE_TYPE_LABELS.get(
            s.get('code_type', ''), s.get('code_type', '')
        )
        with st.expander(
            f"{conf} **{s['code']}** — {s['description']}  "
            f"  `{ctype}`",
            expanded=True
        ):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(
                f"**Confidence:** {s['confidence'].title()}  |  "
                f"**Code type:** {ctype}"
            )

def render_cpt(cpt_suggestions):
    st.markdown("### 🔧 CPT Procedure Codes")
    if not cpt_suggestions:
        st.warning("No CPT suggestions returned")
        return

    for s in cpt_suggestions:
        conf = CONFIDENCE_COLORS.get(s['confidence'], "⚪")
        with st.expander(
            f"{conf} **{s['code']}** — {s['description']}",
            expanded=True
        ):
            st.caption(f"**Rationale:** {s['rationale']}")
            st.caption(
                f"**Confidence:** {s['confidence'].title()}"
            )

def render_prior_auth(prior_auth):
    st.markdown("### 🔐 Prior Authorization Assessment")

    if prior_auth['encounter_requires_auth']:
        st.error(
            f"⚠️ **Authorization required** — "
            f"{prior_auth['summary']}"
        )
    elif prior_auth['payer_type'] == 'self_pay':
        st.info(f"ℹ️ {prior_auth['summary']}")
    else:
        st.success(f"✅ {prior_auth['summary']}")

    # Auth required codes
    if prior_auth['cpt_auth_required']:
        st.markdown("**Procedures requiring authorization:**")
        for item in prior_auth['cpt_auth_required']:
            with st.expander(
                f"🔴 {item['code']} — {item['description']}",
                expanded=True
            ):
                st.caption(item['auth_note'])
                if item['documentation_required']:
                    st.markdown("**Documentation checklist:**")
                    for doc in item['documentation_required']:
                        st.markdown(f"  ☐ {doc}")

    # Auth exempt codes
    if prior_auth['cpt_auth_exempt']:
        st.markdown("**Auth-exempt procedures:**")
        for item in prior_auth['cpt_auth_exempt']:
            st.markdown(
                f"✅ `{item['code']}` — "
                f"{item['description']}"
            )

    # Not applicable (self-pay)
    if prior_auth.get('cpt_auth_not_applicable'):
        st.markdown(
            "**Procedures flagged for financial counseling:**"
        )
        for item in prior_auth['cpt_auth_not_applicable']:
            st.markdown(
                f"💰 `{item['code']}` — "
                f"{item['description']}"
            )
        if prior_auth.get('total_cost'):
            st.info(
                f"Estimated total cost: "
                f"**${prior_auth['total_cost']:,.2f}**  "
                f"— refer to financial assistance program"
            )

    # Not in lookup
    if prior_auth['cpt_not_in_lookup']:
        st.markdown("**Codes requiring manual auth verification:**")
        for item in prior_auth['cpt_not_in_lookup']:
            st.markdown(
                f"❓ `{item['code']}` — "
                f"{item['description']}  "
                f"_{item['note']}_"
            )

def render_medication_review(flag):
    st.markdown("### 💊 Medication Review")
    if flag.get('flagged'):
        st.warning(
            f"⚠️ **Review recommended** — {flag['reason']}"
        )
        st.caption(f"**Action:** {flag['action']}")
    else:
        st.success(
            f"✅ No review required — {flag.get('reason', '')}"
        )

def render_coding_notes(notes):
    if not notes:
        return
    st.markdown("### 📝 Coding Notes")
    for note in notes:
        st.info(f"ℹ️ {note}")

def render_evaluation(evaluation):
    st.markdown("### 📊 Evaluation vs Ground Truth")
    ev = evaluation['icd10_evaluation']

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Precision",
        f"{ev['concept_precision']:.0%}",
        help="% of suggestions matching a ground truth condition"
    )
    col2.metric(
        "Recall",
        f"{ev['concept_recall']:.0%}",
        help="% of ground truth conditions covered"
    )
    col3.metric(
        "Suggested",
        ev['suggested_count'],
        help="ICD-10 codes suggested by AI"
    )
    col4.metric(
        "Ground truth",
        ev['ground_truth_count'],
        help="Conditions recorded in Synthea"
    )

    with st.expander("View match details"):
        for m in ev['match_details']:
            icon = "✅" if m['concept_match'] else "❌"
            st.markdown(
                f"{icon} `{m['suggested_code']}` — "
                f"{m['suggested_desc']}  "
                f"_{m['confidence']} confidence_"
            )

    with st.expander("View ground truth conditions"):
        for gt in evaluation['ground_truth']['conditions']:
            st.markdown(
                f"- {gt['display']}  "
                f"`{gt['code']}`"
            )

def render_data_quality(flags):
    if not flags:
        return
    st.markdown("### ⚠️ Data Quality Flags")
    for flag in flags:
        st.warning(flag)

# ── main app ──────────────────────────────────────────────────────────────────

def main():
    render_header()

    # Encounter selector
    col_select, col_run, col_spacer = st.columns([3, 1, 2])
    with col_select:
        selected_label = st.selectbox(
            "Select encounter",
            options=list(EVALUATION_ENCOUNTERS.keys()),
            index=0,
            label_visibility="collapsed",
        )
    with col_run:
        run_clicked = st.button(
            "▶ Run engine",
            type="primary",
            use_container_width=True,
        )

    st.divider()

    # Session state — persist results across reruns
    if 'results' not in st.session_state:
        st.session_state.results      = None
        st.session_state.last_label   = None

    if run_clicked:
        encounter_id = EVALUATION_ENCOUNTERS[selected_label]
        with st.spinner("Assembling clinical context..."):
            context = build_encounter_context(encounter_id)
        with st.spinner("Running coding engine..."):
            suggestions = suggest_codes(context)
        with st.spinner("Evaluating against ground truth..."):
            evaluation = evaluate_suggestions(
                suggestions, encounter_id
            )
        st.session_state.results    = (context, suggestions,
                                        evaluation)
        st.session_state.last_label = selected_label
        st.success(
            f"✅ Engine completed — "
            f"{len(suggestions.get('icd10_suggestions', []))} "
            f"ICD-10 codes, "
            f"{len(suggestions.get('cpt_suggestions', []))} "
            f"CPT codes suggested"
        )

    # Render results if available
    if st.session_state.results:
        context, suggestions, evaluation = st.session_state.results
        
        # moved header out side the two columns
        # reder header with full-width metrics
        render_encounter_header(context['encounter'])
        left, right = st.columns([1, 1], gap="large")

        # ── LEFT COLUMN — clinical context ────────────────────────
        with left:
            st.markdown("## Clinical Context")
            st.divider()
            render_conditions(context['conditions'])
            st.divider()
            render_procedures(context['procedures'])
            st.divider()
            render_medications(context['medications'])
            st.divider()
            render_observations(context['observations'])
            st.divider()
            render_insurance(context['insurance'])
            if context['metadata']['data_quality_flags']:
                st.divider()
                render_data_quality(
                    context['metadata']['data_quality_flags']
                )

        # ── RIGHT COLUMN — engine output ───────────────────────────
        with right:
            st.markdown("## Coding Suggestions")
            render_icd10(suggestions.get('icd10_suggestions', []))
            st.divider()
            render_cpt(suggestions.get('cpt_suggestions', []))
            st.divider()
            render_prior_auth(
                suggestions.get('prior_auth_assessment', {})
            )
            st.divider()
            render_medication_review(
                suggestions.get('medication_review_flag', {})
            )
            st.divider()
            render_coding_notes(
                suggestions.get('coding_notes', [])
            )
            st.divider()
            render_evaluation(evaluation)

    else:
        st.markdown(
            """
            <div style='text-align:center;padding:60px;
                        color:#888;font-size:1.1rem'>
                Select an encounter above and click
                <strong>▶ Run engine</strong> to begin
            </div>
            """,
            unsafe_allow_html=True,
        )

if __name__ == "__main__":
    main()

