# README

# Project 1 — Clinical Coding Engine

## Problem
Medical coders review clinical records and assign billing codes (ICD-10 for diagnoses, CPT for procedures). Manual coding is slow, inconsistent, and error-prone. Coding errors cause claim denials and revenue loss.

## Solution
An AI-assisted coding engine that:
- Assembles structured clinical context from FHIR data
- Suggests ICD-10 and CPT codes with clinical rationale
- Determines prior authorization requirements by payer type
- Flags medication review triggers
- Evaluates suggestions against ground truth

## Technical Architecture
**Data sources:** PostgreSQL (620 Synthea patient records), Claude API (code suggestions), rules-based prior auth lookup (PRIOR_AUTH_REQUIREMENTS dict)

**Pipeline:** 
1. build_encounter_context() — SQL queries assemble 6 clinical facts
2. suggest_codes() — Claude API with temperature=0 for determinism
3. assess_prior_auth() — Rules-based lookup by payer type
4. evaluate_suggestions() — Concept-level matching vs ground truth

**Key design decisions:**
- Prior auth is rules-based (not AI) for auditability
- Temperature=0 ensures deterministic coding suggestions
- Procedure deduplication reduces token usage
- SNOMED-to-ICD-10 translation delegated to Claude

## Evaluation Results
Tested on 12 Synthea encounters across 4 encounter types.

**Mean precision:** 0.88 — 88% of suggestions correspond to documented conditions
**Mean recall:** 0.93 — 93% of ground truth conditions covered

Precision gaps on post-surgical encounters reflect clinically reasonable code additions beyond ground truth. Recall gaps on ambulatory encounters reflect Z-code translation requiring richer context.

## Production Considerations
- PRIOR_AUTH_REQUIREMENTS is hardcoded from public payer policies. Production would use payer FHIR APIs (CMS mandate by Jan 2027).
- Evaluation uses concept-level matching (Synthea SNOMED vs ICD-10 suggestions). Production would use UMLS crosswalk for exact code comparison.
- Medication review is flagging only (Option A). Full reconciliation requires a clinical drug database.
- Self-pay encounters route to financial counseling, not prior auth — a revenue cycle routing decision.


## Setup

1. Create a `.env` file in the project root:
```bash
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

2. Get your key from https://console.anthropic.com/account/keys

3. The `.env` file is in `.gitignore` and never committed to git.


## How to Run

```bash
cd ~/health-ai-portfolio/project1-coding/app
streamlit run coding_app.py
```

Select an encounter from the dropdown and click **▶ Run engine**.

Requires: PostgreSQL running locally with `health_ai_portfolio` database loaded via `db_loader.py`. API key: `ANTHROPIC_API_KEY` in `.env`.

Demo video: `project1_demo.mp4` (140 seconds overview + evaluation evidence)
