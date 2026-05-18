"""

Change Log
=========================
bug fixes - SODH regex in is_social_determinant function
added - added suggest_codes() that takes the context dict from build_encounter_context() and 
           returns a structured JSON response with: ICD-10 codes, CPT procedures, prior auth flag,
           medication review flag, confidence level per suggestion
added — ground truth comparison
added - Fix the  U07.1 false positive matching function bug in evaluate_suggestions
Updated - Set temperature to 0 for evaluation consistency in suggest_codes()
added - run_batch_evaluation() to run evaluations for all 12 encounters
Updated - Bug Fix - recall exceed 1.0. This happes for CABG encounters (rows 3–6) 
added - introduced prior auth layer.
Updated - get_insurance_context doesn't handle multiple EOBs as a result total_cost when calculating prior auth assessment is wrong.
updated - addedd 33533, 33534, & 93318 to lookup
updated - assess_prior_auth payer_type is "self_pay". Without it CABG encounters show auth_required: false
"""


import json
import psycopg2
import pandas as pd
from datetime import datetime
from pathlib import Path


# ── prior authorization reference data ───────────────────────────────────────

PRIOR_AUTH_REQUIREMENTS = {
    # ── Evaluation & Management ───────────────────────────────────────────────
    "99223": {
        "description":    "Initial hospital care, high complexity",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Inpatient admission requires notification "
                          "within 24hrs for most commercial plans",
        "documentation":  [
            "Admitting diagnosis with ICD-10 code",
            "Estimated length of stay",
            "Treatment plan summary",
        ]
    },
    "99233": {
        "description":    "Subsequent hospital care, high complexity",
        "auth_required":  False,
        "payers":         [],
        "auth_note":      "Covered under inpatient admission auth — "
                          "no separate auth required",
        "documentation":  []
    },
    # ── Cardiology & Cardiac Surgery ─────────────────────────────────────────
    "33510": {
        "description":    "CABG using venous graft, single",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "All payers require prior auth for CABG",
        "documentation":  [
            "Cardiac catheterization results",
            "Failed medical management documentation",
            "Cardiothoracic surgery consultation note",
            "Ejection fraction measurement",
        ]
    },
    "93306": {
        "description":    "Echocardiography with doppler",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Medicare exempt; commercial and Medicaid "
                          "require auth after first study",
        "documentation":  [
            "Clinical indication",
            "Prior echo results if repeat study",
        ]
    },
    "93000": {
        "description":    "Electrocardiogram with interpretation",
        "auth_required":  False,
        "payers":         [],
        "auth_note":      "No prior auth required — covered diagnostic",
        "documentation":  []
    },
    # ── Radiology ─────────────────────────────────────────────────────────────
    "71045": {
        "description":    "Chest X-ray, single view",
        "auth_required":  False,
        "payers":         [],
        "auth_note":      "No prior auth required",
        "documentation":  []
    },
    "71046": {
        "description":    "Chest X-ray, 2 views",
        "auth_required":  False,
        "payers":         [],
        "auth_note":      "No prior auth required",
        "documentation":  []
    },
    "74177": {
        "description":    "CT abdomen and pelvis with contrast",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Most commercial plans require auth for "
                          "advanced imaging",
        "documentation":  [
            "Clinical indication",
            "Failed or inadequate prior imaging",
            "Ordering physician NPI",
        ]
    },
    "70553": {
        "description":    "MRI brain with and without contrast",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "Auth required across all payer types "
                          "for brain MRI",
        "documentation":  [
            "Clinical indication",
            "Neurological examination findings",
            "Prior imaging results",
        ]
    },
    # ── Pulmonary & Critical Care ─────────────────────────────────────────────
    "94640": {
        "description":    "Nebulizer treatment",
        "auth_required":  False,
        "payers":         [],
        "auth_note":      "No prior auth required for acute treatment",
        "documentation":  []
    },
    "94002": {
        "description":    "Ventilation management, hospital inpatient",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Covered under inpatient auth if admission "
                          "pre-authorized; separate auth if initiated "
                          "post-admission",
        "documentation":  [
            "Indication for mechanical ventilation",
            "ABG or SpO2 values",
            "Failed non-invasive ventilation documentation",
        ]
    },
    # ── Orthopedics ───────────────────────────────────────────────────────────
    "27447": {
        "description":    "Total knee arthroplasty",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "Auth required — one of highest-volume "
                          "auth requests nationally",
        "documentation":  [
            "X-ray evidence of joint degeneration",
            "Conservative treatment failure (PT, injections, NSAIDs)",
            "Functional limitation documentation",
            "BMI documentation if >40",
        ]
    },
    "27130": {
        "description":    "Total hip arthroplasty",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "Auth required — document failed "
                          "conservative treatment",
        "documentation":  [
            "X-ray evidence of joint degeneration",
            "Conservative treatment failure",
            "Functional limitation documentation",
        ]
    },
    "29881": {
        "description":    "Knee arthroscopy with meniscectomy",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "Increasingly scrutinized — document "
                          "mechanical symptoms",
        "documentation":  [
            "MRI confirming meniscal tear",
            "Mechanical symptoms (locking, catching)",
            "Failed conservative management",
        ]
    },
    # ── Transplant ────────────────────────────────────────────────────────────
    "50360": {
        "description":    "Renal transplantation",
        "auth_required":  True,
        "payers":         ["commercial", "medicare", "medicaid"],
        "auth_note":      "Requires transplant center approval and "
                          "payer case management in addition to auth",
        "documentation":  [
            "ESRD documentation with GFR values",
            "Transplant center evaluation report",
            "Psychosocial evaluation",
            "Financial clearance documentation",
        ]
    },
    # ── Mental Health ─────────────────────────────────────────────────────────
    "90837": {
        "description":    "Psychotherapy, 60 minutes",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Most plans auth 6–12 sessions initially; "
                          "continuation requires outcomes documentation",
        "documentation":  [
            "DSM-5 diagnosis",
            "Treatment plan with measurable goals",
            "Functional impairment documentation",
        ]
    },
    "90853": {
        "description":    "Group psychotherapy",
        "auth_required":  True,
        "payers":         ["commercial", "medicaid"],
        "auth_note":      "Auth required; lower threshold than "
                          "individual therapy",
        "documentation":  [
            "DSM-5 diagnosis",
            "Group treatment plan",
        ]
    },
    # ── CABG ─────────────────────────────────────────────────────────
    "33533": {
        "description":   "CABG using arterial graft, single",
        "auth_required": True,
        "payers":        ["commercial", "medicare", "medicaid"],
        "auth_note":     "All payers require prior auth for CABG — "
                         "obtain before scheduling",
        "documentation": [
            "Cardiac catheterization results",
            "Failed medical management documentation",
            "Cardiothoracic surgery consultation note",
            "Ejection fraction measurement",
        ]
    },
    "33534": {
        "description":   "CABG using arterial graft, two vessels",
        "auth_required": True,
        "payers":        ["commercial", "medicare", "medicaid"],
        "auth_note":     "All payers require prior auth for CABG — "
                         "obtain before scheduling",
        "documentation": [
            "Cardiac catheterization results",
            "Failed medical management documentation",
            "Cardiothoracic surgery consultation note",
            "Ejection fraction measurement",
        ]
    },
    # ── ─Echocardiography────────────────────────────────────────────────────────
    "93318": {
        "description":   "Echocardiography, transesophageal, "
                         "monitoring",
        "auth_required": True,
        "payers":        ["commercial", "medicaid"],
        "auth_note":     "Medicare generally bundles with surgical "
                         "procedure — commercial and Medicaid may "
                         "require separate auth",
        "documentation": [
            "Surgical procedure requiring hemodynamic monitoring",
            "Ordering physician attestation",
        ]
    }
}

# Payer type mapping — classify insurer names to payer types
PAYER_TYPE_MAP = {
    "medicare":              "medicare",
    "dual eligible":         "medicare",
    "medicaid":              "medicaid",
    "humana":                "commercial",
    "anthem":                "commercial",
    "unitedhealthcare":      "commercial",
    "cigna health":          "commercial",
    "blue cross blue shield": "commercial",
    "aetna":                 "commercial",
    "no_insurance":          "self_pay",
}

def get_payer_type(insurer_display):
    """Map insurer display name to payer category."""
    if not insurer_display:
        return "unknown"
    return PAYER_TYPE_MAP.get(
        insurer_display.lower(), "commercial"
    )

# ── database connection ───────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        dbname="health_ai_portfolio",
        host="localhost"
    )

def query(sql, params=None, conn=None):
    close_after = conn is None
    if conn is None:
        conn = get_conn()
    df = pd.read_sql(sql, conn, params=params)
    if close_after:
        conn.close()
    return df

# ── helper functions ──────────────────────────────────────────────────────────

def format_date(date_val):
    """Convert date/datetime to readable string."""
    if date_val is None:
        return None
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%Y-%m-%d')
    return str(date_val)[:10]



import re

def is_social_determinant(display):
    sdoh_patterns = [
        r'\bemployment\b',       r'\bstress\b',
        r'\bsocial contact\b',   r'\bviolence\b',
        r'\blabor force\b',      r'\bmedication review\b',
        r'\bhousing\b',          r'\beducation\b',
        r'\bfood\b',             r'\btransport\b',
        r'\bfinancial\b',        r'\bliteracy\b',
    ]
    if not display:
        return False
    return any(
        re.search(pattern, display.lower())
        for pattern in sdoh_patterns
    )

# ── core assembly functions ───────────────────────────────────────────────────

def get_encounter_header(encounter_id, conn):
    """Fetch encounter metadata."""
    df = query("""
        SELECT
            e.id,
            e.patient_id,
            e.encounter_class,
            e.encounter_type,
            e.start_date,
            e.end_date,
            e.reason_display,
            ROUND(
                EXTRACT(EPOCH FROM (e.end_date - e.start_date))
                / 3600, 1
            )                       AS duration_hours,
            p.gender,
            p.birth_date,
            DATE_PART('year', AGE(e.start_date, p.birth_date::timestamp))
                                    AS age_at_encounter
        FROM encounters e
        JOIN patients p ON p.id = e.patient_id
        WHERE e.id = %(encounter_id)s
    """, params={'encounter_id': encounter_id}, conn=conn)

    if df.empty:
        raise ValueError(f"Encounter {encounter_id} not found")

    row = df.iloc[0]
    return {
        'encounter_id':    row['id'],
        'patient_id':      row['patient_id'],
        'encounter_class': row['encounter_class'],
        'encounter_type':  row['encounter_type'],
        'encounter_date':  format_date(row['start_date']),
        'duration_hours':  float(row['duration_hours'])
                           if row['duration_hours'] else None,
        'reason':          row['reason_display'],
        'patient_gender':  row['gender'],
        'patient_age':     int(row['age_at_encounter'])
                           if row['age_at_encounter'] else None,
    }

def get_conditions(encounter_id, conn):
    """
    Fetch conditions for this encounter.
    Separates clinical diagnoses from social determinants.
    """
    df = query("""
        SELECT
            code,
            display,
            clinical_status,
            recorded_date
        FROM conditions
        WHERE encounter_id = %(encounter_id)s
        ORDER BY recorded_date
    """, params={'encounter_id': encounter_id}, conn=conn)

    diagnoses   = []
    sdoh_flags  = []

    for _, row in df.iterrows():
        entry = {
            'code':    row['code'],
            'display': row['display'],
            'status':  row['clinical_status'],
        }
        if is_social_determinant(row['display']):
            sdoh_flags.append(entry)
        else:
            diagnoses.append(entry)

    return {
        'diagnoses':            diagnoses,
        'social_determinants':  sdoh_flags,
        'total_conditions':     len(df),
        'data_quality': {
            'has_conditions': len(df) > 0,
            'flag': None if len(df) > 0
                    else 'NO_CONDITIONS — coding context limited'
        }
    }

def get_procedures(encounter_id, conn):
    df = query("""
        SELECT
            code,
            display,
            COUNT(*)    AS occurrence_count,
            MIN(performed_date) AS first_performed,
            status
        FROM procedures
        WHERE encounter_id = %(encounter_id)s
            AND status = 'completed'
        GROUP BY code, display, status
        ORDER BY occurrence_count DESC
    """, params={'encounter_id': encounter_id}, conn=conn)

    admin_terms = [
        'medication reconciliation', 'review of systems',
        'assessment of health', 'anticipatory guidance',
        'depression screening', 'anxiety screening',
        'alcohol screening', 'drug abuse screening',
        'documentation of',
    ]

    clinical = []
    admin    = []

    for _, row in df.iterrows():
        display_lower = (row['display'] or '').lower()
        is_admin = any(term in display_lower for term in admin_terms)
        entry = {
            'code':             row['code'],
            'display':          row['display'],
            'occurrence_count': int(row['occurrence_count']),
        }
        if is_admin:
            admin.append(entry)
        else:
            clinical.append(entry)

    return {
        'clinical_procedures':       clinical,
        'administrative_procedures': admin,
        'total_procedures':          len(df),
        'data_quality': {
            'high_procedure_count': len(df) > 20,
            'flag': (
                f'HIGH PROCEDURE COUNT ({len(df)}) — '
                f'verify clinical vs administrative split'
                if len(df) > 20 else None
            )
        }
    }

def get_medications(encounter_id, conn):
    df = query("""
        SELECT
            medication_code,
            medication_display,
            status,
            COUNT(*)    AS occurrence_count
        FROM medication_requests
        WHERE encounter_id = %(encounter_id)s
            AND status IN ('active', 'completed')
            AND medication_display IS NOT NULL
        GROUP BY medication_code, medication_display, status
        ORDER BY occurrence_count DESC
    """, params={'encounter_id': encounter_id}, conn=conn)

    medications = []
    for _, row in df.iterrows():
        medications.append({
            'code':             row['medication_code'],
            'display':          row['medication_display'],
            'status':           row['status'],
            'occurrence_count': int(row['occurrence_count']),
        })

    return {
        'medications': medications,
        'count':       len(medications),
        'data_quality': {
            'has_medications': len(medications) > 0,
            'flag': (
                'NO_MEDICATIONS — verify if encounter '
                'type expects medication orders'
                if len(medications) == 0 else None
            )
        }
    }


def get_observations(encounter_id, conn):
    """
    Fetch key observations — vitals and labs only.
    Excludes survey responses and administrative observations
    to keep context concise.
    """
    df = query("""
        SELECT
            code,
            display,
            value_quantity,
            value_unit,
            value_string,
            effective_date
        FROM observations
        WHERE encounter_id = %(encounter_id)s
            AND status = 'final'
            AND (
                value_quantity IS NOT NULL
                OR value_string IS NOT NULL
            )
        ORDER BY effective_date
        LIMIT 30
    """, params={'encounter_id': encounter_id}, conn=conn)

    observations = []
    for _, row in df.iterrows():
        value = (
            f"{row['value_quantity']} {row['value_unit']}"
            if row['value_quantity'] is not None
            else row['value_string']
        )
        if not value or str(value).strip() == 'None None':
            continue
        observations.append({
            'display': row['display'],
            'value':   str(value).strip(),
            'date':    format_date(row['effective_date']),
        })

    return {
        'observations': observations,
        'count':        len(observations),
    }


def get_insurance_context(encounter_id, conn):
    df = query("""
        SELECT
            SUM(eob.total_cost)                     AS total_cost,
            SUM(eob.insurance_paid)                 AS insurance_paid,
            MAX(eob.resource -> 'insurer'
                ->> 'display')                      AS insurer
        FROM explanation_of_benefits eob
        WHERE eob.encounter_id = %(encounter_id)s
            AND eob.total_cost  > 0
    """, params={'encounter_id': encounter_id}, conn=conn)

    if df.empty or df.iloc[0]['total_cost'] is None:
        return {
            'insurer':                'Unknown',
            'total_cost':             None,
            'insurance_paid':         None,
            'patient_responsibility': None,
            'requires_prior_auth':    False,
        }

    row         = df.iloc[0]
    total       = float(row['total_cost'])
    paid        = float(row['insurance_paid']) \
                  if row['insurance_paid'] else 0
    insurer     = row['insurer'] or 'Unknown'

    return {
        'insurer':                insurer,
        'total_cost':             round(total, 2),
        'insurance_paid':         round(paid, 2),
        'patient_responsibility': round(total - paid, 2),
        'requires_prior_auth':    total > 5000
                                  and insurer != 'NO_INSURANCE',
    }



# ── main assembly function ────────────────────────────────────────────────────

def build_encounter_context(encounter_id):
    """
    Assemble a complete clinical context dict for one encounter.

    This is the primary input to all AI functions in this project.
    Design principles:
    - Clinically meaningful fields only — no FHIR metadata
    - Explicit data quality flags — no silent empty lists
    - Separation of clinical vs administrative data
    - Insurance context included for prior auth relevance

    Args:
        encounter_id: UUID string of the encounter

    Returns:
        dict: structured clinical context ready for Claude API
    """
    conn = get_conn()

    try:
        header      = get_encounter_header(encounter_id, conn)
        conditions  = get_conditions(encounter_id, conn)
        procedures  = get_procedures(encounter_id, conn)
        medications = get_medications(encounter_id, conn)
        observations = get_observations(encounter_id, conn)
        insurance   = get_insurance_context(encounter_id, conn)

        context = {
            'encounter':    header,
            'conditions':   conditions,
            'procedures':   procedures,
            'medications':  medications,
            'observations': observations,
            'insurance':    insurance,
            'metadata': {
                'assembled_at':   datetime.now().isoformat(),
                'encounter_id':   encounter_id,
                'data_quality_flags': [
                    flag for flag in [
                        conditions['data_quality']['flag'],
                        procedures['data_quality']['flag'],
                        medications['data_quality']['flag'],
                    ]
                    if flag is not None
                ]
            }
        }

        return context

    finally:
        conn.close()

#
#  The suggest_codes() takes the context dict from build_encounter_context() and returns structured json response with
#  Suggested ICD-10 diagnosis codes with rationale
#  Suggested CPT procedure codes with rationale
#  A prior auth flag with justification
#  A medication review flag (Option A — flag only)
#  Confidence level per suggestion
#
#
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

def format_context_for_prompt(context):
    """
    Convert the context dict into a structured clinical
    summary string for the prompt.
    Deliberately human-readable — not raw JSON.
    """
    enc  = context['encounter']
    cond = context['conditions']
    proc = context['procedures']
    meds = context['medications']
    obs  = context['observations']
    ins  = context['insurance']

    lines = [
        "ENCOUNTER SUMMARY",
        "─" * 40,
        f"Date:              {enc['encounter_date']}",
        f"Type:              {enc['encounter_type']}",
        f"Setting:           {enc['encounter_class']} "
        f"({'Inpatient' if enc['encounter_class'] == 'IMP' else 'Ambulatory'
            if enc['encounter_class'] == 'AMB' else enc['encounter_class']})",
        f"Duration:          {enc['duration_hours']} hours",
        f"Reason for visit:  {enc['reason'] or 'Not documented'}",
        f"Patient:           {enc['patient_gender'].title()}, "
        f"age {enc['patient_age']}",
        "",
        "DIAGNOSES",
        "─" * 40,
    ]

    if cond['diagnoses']:
        for d in cond['diagnoses']:
            lines.append(
                f"  • {d['display']} "
                f"[existing code: {d['code']}] "
                f"(status: {d['status']})"
            )
    else:
        lines.append("  No diagnoses documented")

    if cond['social_determinants']:
        lines += ["", "SOCIAL DETERMINANTS (Z-code candidates)"]
        for s in cond['social_determinants']:
            lines.append(f"  • {s['display']}")

    lines += ["", "PROCEDURES PERFORMED", "─" * 40]
    if proc['clinical_procedures']:
        for p in proc['clinical_procedures']:
            count = p.get('occurrence_count', 1)
            suffix = f" (×{count})" if count > 1 else ""
            lines.append(f"  • {p['display']}{suffix} [code: {p['code']}]")
    else:
        lines.append("  No clinical procedures documented")

    lines += ["", "MEDICATIONS ORDERED", "─" * 40]
    if meds['medications']:
        for m in meds['medications']:
            count = m.get('occurrence_count', 1)
            suffix = f" (×{count})" if count > 1 else ""
            lines.append(
                f"  • {m['display']}{suffix} "
                f"[RxNorm: {m['code']}]"
            )
    else:
        lines.append("  No medications documented")

    lines += ["", "KEY OBSERVATIONS (vitals & labs)", "─" * 40]
    if obs['observations']:
        for o in obs['observations'][:15]:  # cap at 15
            lines.append(f"  • {o['display']}: {o['value']}")
    else:
        lines.append("  No observations documented")

    lines += [
        "",
        "INSURANCE",
        "─" * 40,
        f"  Payer:                {ins['insurer']}",
        f"  Total cost:           ${ins['total_cost']:,.2f}"
        if ins['total_cost'] else "  Total cost: Unknown",
        f"  Insurance paid:       ${ins['insurance_paid']:,.2f}"
        if ins['insurance_paid'] else "  Insurance paid: Unknown",
        f"  Patient responsibility: ${ins['patient_responsibility']:,.2f}"
        if ins['patient_responsibility'] else "",
        f"  Prior auth required:  "
        f"{'YES' if ins['requires_prior_auth'] else 'NO'}",
    ]

    # Data quality flags
    flags = context['metadata'].get('data_quality_flags', [])
    if flags:
        lines += ["", "DATA QUALITY FLAGS", "─" * 40]
        for flag in flags:
            lines.append(f"  ⚠ {flag}")

    return "\n".join(lines)


def build_coding_prompt(context):
    """
    Build the system and user prompts for the coding task.
    Separation of system and user is intentional —
    system defines the role and output contract,
    user provides the clinical data.
    """
    system_prompt = """You are a certified professional medical coder 
(CPC) reviewing an encounter summary to suggest appropriate billing codes.

Your task is to return a JSON object with the following structure:

{
  "icd10_suggestions": [
    {
      "code": "string — ICD-10-CM code e.g. J18.9",
      "description": "string — official code description",
      "rationale": "string — why this code applies to this encounter",
      "confidence": "high | medium | low",
      "code_type": "primary | secondary | additional"
    }
  ],
  "cpt_suggestions": [
    {
      "code": "string — CPT code e.g. 99233",
      "description": "string — procedure description",
      "rationale": "string — why this code applies",
      "confidence": "high | medium | low"
    }
  ],
  "prior_auth_assessment": {
    "required": true | false,
    "reason": "string — clinical justification",
    "supporting_codes": ["list of ICD-10 codes that support auth"]
  },
  "medication_review_flag": {
    "flagged": true | false,
    "reason": "string — why flagged or not",
    "action": "string — recommended workflow action"
  },
  "coding_notes": [
    "string — any important coding guidance, sequencing rules, 
     or documentation gaps that affect code selection"
  ]
}

Rules you must follow:
1. Return ONLY valid JSON — no preamble, no markdown, 
   no explanation outside the JSON structure
2. ICD-10 primary diagnosis must reflect the main reason 
   for the encounter, not a chronic background condition
3. Suggest CPT E&M code appropriate for the encounter 
   setting and complexity
4. Flag medication review if 5 or more medications are 
   present OR any high-risk drug class is identified
5. If a social determinant is present assign the 
   appropriate Z55-Z65 ICD-10 code
6. Note any documentation gaps that would prevent 
   a coder from selecting a more specific code"""

    clinical_summary = format_context_for_prompt(context)

    user_prompt = f"""Please review the following encounter and suggest 
appropriate ICD-10-CM and CPT billing codes.

{clinical_summary}

Return your response as a valid JSON object matching 
the structure specified."""

    return system_prompt, user_prompt


def assess_prior_auth(cpt_suggestions, insurer, total_cost):
    payer_type    = get_payer_type(insurer)
    auth_required = []
    auth_exempt   = []
    auth_na       = []       # auth concept doesn't apply
    not_in_lookup = []

    for cpt in cpt_suggestions:
        code = cpt.get('code')
        if not code:
            continue

        rule = PRIOR_AUTH_REQUIREMENTS.get(code)

        if rule is None:
            not_in_lookup.append({
                'code':        code,
                'description': cpt.get('description', ''),
                'status':      'NOT_IN_LOOKUP',
                'note':        'Verify auth requirement with payer — '
                               'code not in reference table'
            })
            continue

        # Self-pay and unknown payers — auth concept
        # doesn't apply, report separately
        if payer_type in ('self_pay', 'unknown'):
            auth_na.append({
                'code':         code,
                'description':  rule['description'],
                'auth_required': False,
                'payer_type':   payer_type,
                'auth_note':    (
                    'Prior authorization not applicable — '
                    'no insurance payer. Route to financial '
                    'counseling for cost estimation.'
                    if payer_type == 'self_pay'
                    else
                    'Payer type unknown — verify auth '
                    'requirement directly with payer.'
                ),
                'documentation_required': []
            })
            continue

        requires_for_payer = (
            rule['auth_required']
            and payer_type in rule['payers']
        )

        entry = {
            'code':           code,
            'description':    rule['description'],
            'auth_required':  requires_for_payer,
            'payer_type':     payer_type,
            'auth_note':      rule['auth_note'],
            'documentation_required': (
                rule['documentation']
                if requires_for_payer else []
            )
        }

        if requires_for_payer:
            auth_required.append(entry)
        else:
            auth_exempt.append(entry)

    encounter_requires_auth = len(auth_required) > 0

    all_docs = []
    for item in auth_required:
        for doc in item['documentation_required']:
            if doc not in all_docs:
                all_docs.append(doc)

    # Summary message varies by payer type
    if payer_type == 'self_pay':
        summary = (
            f"Prior authorization not applicable — "
            f"patient is uninsured. "
            f"{len(auth_na)} procedure(s) flagged for "
            f"financial counseling review. "
            f"Estimated cost: ${total_cost:,.2f}"
            if total_cost else
            f"Prior authorization not applicable — "
            f"patient is uninsured."
        )
    elif encounter_requires_auth:
        summary = (
            f"{len(auth_required)} of "
            f"{len(cpt_suggestions)} suggested CPT codes "
            f"require prior authorization from {insurer} "
            f"({payer_type})"
        )
    else:
        summary = (
            f"No prior authorization required for "
            f"{insurer} ({payer_type}) — "
            f"all suggested procedures are auth-exempt"
        )

    return {
        'encounter_requires_auth':  encounter_requires_auth,
        'payer_type':               payer_type,
        'insurer':                  insurer,
        'total_cost':               total_cost,
        'cpt_auth_required':        auth_required,
        'cpt_auth_exempt':          auth_exempt,
        'cpt_auth_not_applicable':  auth_na,
        'cpt_not_in_lookup':        not_in_lookup,
        'documentation_checklist':  all_docs,
        'summary':                  summary
    }

def suggest_codes(context):
    """
    Call Claude API with encounter context and return
    structured coding suggestions.

    Args:
        context: dict from build_encounter_context()

    Returns:
        dict: structured coding suggestions
    """

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    system_prompt, user_prompt = build_coding_prompt(context)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        temperature=0,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        raw_text = raw_text.rsplit("```", 1)[0]

    suggestions = json.loads(raw_text)

    # Replace Claude's prior_auth_assessment with
    # our rules-based layer — more reliable and auditable
    suggestions['prior_auth_assessment'] = assess_prior_auth(
        cpt_suggestions=suggestions.get('cpt_suggestions', []),
        insurer=context['insurance']['insurer'],
        total_cost=context['insurance']['total_cost'],
    )

    suggestions['_meta'] = {
        'encounter_id':   context['encounter']['encounter_id'],
        'encounter_type': context['encounter']['encounter_type'],
        'encounter_date': context['encounter']['encounter_date'],
        'model':          response.model,
        'input_tokens':   response.usage.input_tokens,
        'output_tokens':  response.usage.output_tokens,
        'prompt_version': 'v1.0',
    }

    return suggestions


### 1b evalauete_suggestions
def evaluate_suggestions(suggestions, encounter_id, conn=None):
    close_after = conn is None
    if conn is None:
        conn = get_conn()

    gt_conditions = query("""
        SELECT code, display, clinical_status
        FROM conditions
        WHERE encounter_id = %(eid)s
    """, params={'eid': encounter_id}, conn=conn)

    gt_encounter = query("""
        SELECT reason_display, encounter_type
        FROM encounters
        WHERE id = %(eid)s
    """, params={'eid': encounter_id}, conn=conn)

    gt_procedures = query("""
        SELECT code, display
        FROM procedures
        WHERE encounter_id = %(eid)s
        GROUP BY code, display
    """, params={'eid': encounter_id}, conn=conn)

    if close_after:
        conn.close()

    suggested_icd10 = {
        s['code']: s for s in suggestions.get('icd10_suggestions', [])
    }
    suggested_cpt = {
        s['code']: s for s in suggestions.get('cpt_suggestions', [])
    }

    # Build full matching corpus:
    # conditions + encounter reason + encounter type
    gt_displays = [
        row['display'].lower()
        for _, row in gt_conditions.iterrows()
    ]
    if not gt_encounter.empty:
        reason   = gt_encounter.iloc[0]['reason_display']
        enc_type = gt_encounter.iloc[0]['encounter_type']
        if reason:
            gt_displays.append(reason.lower())
        if enc_type:
            gt_displays.append(enc_type.lower())

    # Matching loop
    icd10_matches      = []
    gt_matched_indices = set()

    for code, suggestion in suggested_icd10.items():
        desc_lower      = suggestion['description'].lower()
        rationale_lower = suggestion.get('rationale', '').lower()
        matched_gt_idx  = None

        for idx, gt_disp in enumerate(gt_displays):
            significant_words = [
                w for w in gt_disp.split() if len(w) > 4
            ]
            if not significant_words:
                continue
            word_match = any(
                word in desc_lower or word in rationale_lower
                for word in significant_words
            )
            if word_match:
                matched_gt_idx = idx
                break

        is_match = matched_gt_idx is not None
        if is_match:
            gt_matched_indices.add(matched_gt_idx)

        icd10_matches.append({
            'suggested_code': code,
            'suggested_desc': suggestion['description'],
            'confidence':     suggestion['confidence'],
            'code_type':      suggestion['code_type'],
            'concept_match':  is_match,
        })

    # Metrics
    total_suggested       = len(icd10_matches)
    concept_matched       = sum(1 for m in icd10_matches
                                if m['concept_match'])
    gt_conditions_matched = len(gt_matched_indices)
    recall_denominator    = len(gt_conditions)

    evaluation = {
        'encounter_id': encounter_id,
        'icd10_evaluation': {
            'suggested_count':       total_suggested,
            'ground_truth_count':    recall_denominator,
            'concept_matches':       concept_matched,
            'gt_conditions_matched': gt_conditions_matched,
            'concept_precision':     round(
                concept_matched / total_suggested, 2
            ) if total_suggested > 0 else 0,
            'concept_recall':        round(
                gt_conditions_matched / recall_denominator, 2
            ) if recall_denominator > 0 else 0,
            'match_details':         icd10_matches,
        },
        'cpt_evaluation': {
            'suggested_count': len(suggested_cpt),
            'suggested_codes': list(suggested_cpt.keys()),
            'note': (
                'CPT exact match not possible against '
                'Synthea SNOMED procedure codes — '
                'manual clinical review required'
            )
        },
        'ground_truth': {
            'conditions': gt_conditions.to_dict('records'),
            'procedures': gt_procedures.to_dict('records'),
        }
    }

    return evaluation

def run_batch_evaluation(encounter_ids):
    """
    Run suggest_codes + evaluate_suggestions
    across all evaluation encounters.
    Saves results to JSON for analysis.
    """
    results = []

    for i, eid in enumerate(encounter_ids):
        print(f"Processing {i+1}/{len(encounter_ids)}: {eid[:8]}...")
        #print(f"Checking for function: {'build_encounter_context' in globals()}")

        try:



            context     = build_encounter_context(eid)
            suggestions = suggest_codes(context)

            # Temporarily add this to run_batch_evaluation()
            # inside the try block, after suggest_codes():
            print(f"  Suggestions keys: {list(suggestions.keys())}")
            print(f"  ICD10 count: {len(suggestions.get('icd10_suggestions', []))}")

            evaluation  = evaluate_suggestions(suggestions, eid)

            results.append({
                'encounter_id':   eid,
                'encounter_type': context['encounter']['encounter_type'],
                'encounter_class': context['encounter']['encounter_class'],
                'suggestions':    suggestions,
                'evaluation':     evaluation,
                'status':         'success'
            })

        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'encounter_id': eid,
                'status':       'error',
                'error':        str(e)
            })


    # After the loop, print errors:
    errors = [r for r in results if r['status'] == 'error']
    for e in errors:
        print(f"\nError on {e['encounter_id'][:8]}: {e['error']}")    


    # Save full results
    output_path = Path(
        '../data/evaluation_results_v1.json'
    )
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    successful = [r for r in results if r['status'] == 'success']
    print(f"\n{'='*50}")
    print(f"Completed: {len(successful)}/{len(results)} encounters")
    print(f"\nPer-encounter results:")
    print(f"{'Encounter':<12} {'Type':<35} "
          f"{'Precision':>10} {'Recall':>8} "
          f"{'ICD suggested':>14} {'GT conditions':>14}")
    print("-" * 95)

    for r in successful:
        ev  = r['evaluation']['icd10_evaluation']
        enc = r['encounter_type'][:33]
        print(
            f"{r['encounter_id'][:8]:<12} "
            f"{enc:<35} "
            f"{ev['concept_precision']:>10.2f} "
            f"{ev['concept_recall']:>8.2f} "
            f"{ev['suggested_count']:>14} "
            f"{ev['ground_truth_count']:>14}"
        )

    # Aggregate metrics
    precisions = [
        r['evaluation']['icd10_evaluation']['concept_precision']
        for r in successful
    ]
    recalls = [
        r['evaluation']['icd10_evaluation']['concept_recall']
        for r in successful
    ]

    print(f"\n{'='*50}")
    print(f"AGGREGATE METRICS (n={len(successful)} encounters)")
    print(f"Mean precision: {sum(precisions)/len(precisions):.2f}")
    print(f"Mean recall:    {sum(recalls)/len(recalls):.2f}")
    print(f"Min precision:  {min(precisions):.2f}")
    print(f"Min recall:     {min(recalls):.2f}")

    return results
