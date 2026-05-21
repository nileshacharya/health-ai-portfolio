import json
import psycopg2
from psycopg2.extras import Json
from pathlib import Path

DB_CONFIG = {"dbname": "health_ai_portfolio", "host": "localhost"}
FHIR_DIR = Path("~/health-ai-portfolio/data/synthea/output/fhir").expanduser()

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def strip_ref(ref):
    """Strip urn:uuid: prefix from FHIR references."""
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return ref.replace("urn:uuid:", "")
    if "/" in ref:
        return ref.split("/")[-1]
    return ref

def get_code(resource, field="code"):
    """Extract primary code from a CodeableConcept field."""
    cc = resource.get(field, {})
    if isinstance(cc, list):
        cc = cc[0] if cc else {}
    codings = cc.get("coding", [])
    return codings[0].get("code") if codings else None

def get_display(resource, field="code"):
    """Extract display text from a CodeableConcept field."""
    cc = resource.get(field, {})
    if isinstance(cc, list):
        cc = cc[0] if cc else {}
    if cc.get("text"):
        return cc["text"]
    codings = cc.get("coding", [])
    return codings[0].get("display") if codings else None

def create_tables(conn):
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id           TEXT PRIMARY KEY,
            birth_date   DATE,
            gender       TEXT,
            city         TEXT,
            state        TEXT,
            resource     JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS encounters (
            id               TEXT PRIMARY KEY,
            patient_id       TEXT,
            start_date       TIMESTAMP,
            end_date         TIMESTAMP,
            encounter_class  TEXT,
            encounter_type   TEXT,
            reason_display   TEXT,
            resource         JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conditions (
            id               TEXT PRIMARY KEY,
            patient_id       TEXT,
            encounter_id     TEXT,
            code             TEXT,
            display          TEXT,
            recorded_date    TIMESTAMP,
            clinical_status  TEXT,
            resource         JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS procedures (
            id              TEXT PRIMARY KEY,
            patient_id      TEXT,
            encounter_id    TEXT,
            code            TEXT,
            display         TEXT,
            performed_date  TIMESTAMP,
            status          TEXT,
            resource        JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS medication_requests (
            id                  TEXT PRIMARY KEY,
            patient_id          TEXT,
            encounter_id        TEXT,
            medication_code     TEXT,
            medication_display  TEXT,
            authored_on         TIMESTAMP,
            status              TEXT,
            intent              TEXT,
            resource            JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id              TEXT PRIMARY KEY,
            patient_id      TEXT,
            encounter_id    TEXT,
            code            TEXT,
            display         TEXT,
            value_quantity  NUMERIC,
            value_unit      TEXT,
            value_string    TEXT,
            effective_date  TIMESTAMP,
            status          TEXT,
            resource        JSONB
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS explanation_of_benefits (
            id              TEXT PRIMARY KEY,
            patient_id      TEXT,
            encounter_id    TEXT,
            status          TEXT,
            total_cost      NUMERIC,
            insurance_paid  NUMERIC,
            resource        JSONB
        )
    """)

    conn.commit()
    cur.close()
    print("Tables created.")

def load_resource(cur, resource):
    rt  = resource.get("resourceType")
    rid = resource.get("id")
    if not rt or not rid:
        return

    if rt == "Patient":
        addr = resource.get("address", [{}])[0]
        cur.execute("""
            INSERT INTO patients
                (id, birth_date, gender, city, state, resource)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            resource.get("birthDate"),
            resource.get("gender"),
            addr.get("city"),
            addr.get("state"),
            Json(resource)
        ))

    elif rt == "Encounter":
        period   = resource.get("period", {})
        enc_type = None
        types    = resource.get("type", [])
        if types:
            cc       = types[0]
            enc_type = cc.get("text") or (
                cc.get("coding", [{}])[0].get("display")
            )
        reason_list    = resource.get("reasonCode", [])
        reason_display = get_display({"code": reason_list[0]}) if reason_list else None

        cur.execute("""
            INSERT INTO encounters
                (id, patient_id, start_date, end_date,
                 encounter_class, encounter_type, reason_display, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("subject", {}).get("reference")),
            period.get("start"),
            period.get("end"),
            resource.get("class", {}).get("code"),
            enc_type,
            reason_display,
            Json(resource)
        ))

    elif rt == "Condition":
        onset = (resource.get("onsetDateTime")
                 or resource.get("recordedDate"))
        status = (resource.get("clinicalStatus", {})
                         .get("coding", [{}])[0].get("code"))
        cur.execute("""
            INSERT INTO conditions
                (id, patient_id, encounter_id, code, display,
                 recorded_date, clinical_status, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("subject",  {}).get("reference")),
            strip_ref(resource.get("encounter", {}).get("reference")),
            get_code(resource),
            get_display(resource),
            onset,
            status,
            Json(resource)
        ))

    elif rt == "Procedure":
        performed = (resource.get("performedDateTime")
                     or resource.get("performedPeriod", {}).get("start"))
        cur.execute("""
            INSERT INTO procedures
                (id, patient_id, encounter_id, code, display,
                 performed_date, status, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("subject",  {}).get("reference")),
            strip_ref(resource.get("encounter", {}).get("reference")),
            get_code(resource),
            get_display(resource),
            performed,
            resource.get("status"),
            Json(resource)
        ))

    elif rt == "MedicationRequest":
        med      = resource.get("medicationCodeableConcept", {})
        codings  = med.get("coding", [])
        med_code = codings[0].get("code")     if codings else None
        med_disp = med.get("text") or (codings[0].get("display") if codings else None)

        cur.execute("""
            INSERT INTO medication_requests
                (id, patient_id, encounter_id, medication_code,
                 medication_display, authored_on, status, intent, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("subject",  {}).get("reference")),
            strip_ref(resource.get("encounter", {}).get("reference")),
            med_code,
            med_disp,
            resource.get("authoredOn"),
            resource.get("status"),
            resource.get("intent"),
            Json(resource)
        ))

    elif rt == "Observation":
        vq = resource.get("valueQuantity", {})
        vs = resource.get("valueString")
        if not vs and resource.get("valueCodeableConcept"):
            vs = resource["valueCodeableConcept"].get("text")

        cur.execute("""
            INSERT INTO observations
                (id, patient_id, encounter_id, code, display,
                 value_quantity, value_unit, value_string,
                 effective_date, status, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("subject",  {}).get("reference")),
            strip_ref(resource.get("encounter", {}).get("reference")),
            get_code(resource),
            get_display(resource),
            vq.get("value") if vq else None,
            vq.get("unit")  if vq else None,
            vs,
            resource.get("effectiveDateTime"),
            resource.get("status"),
            Json(resource)
        ))

    elif rt == "ExplanationOfBenefit":
        total_cost = insurance_paid = None
        for t in resource.get("total", []):
            cat = t.get("category", {}).get("coding", [{}])[0].get("code", "")
            val = t.get("amount", {}).get("value")
            if cat == "submitted":
                total_cost    = val


        insurance_paid =(resource.get("payment", {})
                                 .get("amount", {{})
                                 .get("value"))

        cur.execute("""
            INSERT INTO explanation_of_benefits
                (id, patient_id, encounter_id, status,
                 total_cost, insurance_paid, resource)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """, (
            rid,
            strip_ref(resource.get("patient", {}).get("reference")),
            strip_ref(
                resource.get("item", [{}])[0]
                .get("encounter", [{}])[0]
                .get("reference")
),
            resource.get("status"),
            total_cost,
            insurance_paid,
            Json(resource)
        ))

def load_all_bundles():
    conn = get_conn()
    create_tables(conn)

    files  = list(FHIR_DIR.glob("*.json"))
    counts = {}
    errors = 0

    print(f"Loading {len(files)} patient bundles...\n")

    for i, filepath in enumerate(files):
        cur = conn.cursor()
        try:
            with open(filepath) as f:
                bundle = json.load(f)

            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                rt       = resource.get("resourceType")
                if rt:
                    counts[rt] = counts.get(rt, 0) + 1
                    try:
                        load_resource(cur, resource)
                    except Exception:
                        errors += 1

            conn.commit()
        except Exception as e:
            print(f"  Error on {filepath.name}: {e}")
        finally:
            cur.close()

        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(files)} bundles processed...")

    conn.close()

    print(f"\nLoad complete. {errors} skipped rows.\n")
    print("Resource counts loaded:")
    for rt, n in sorted(counts.items(), key=lambda x: -x[1]):
        marker = " ★" if rt in {"Condition","Procedure","MedicationRequest",
                                 "Observation","Encounter","ExplanationOfBenefit"} else ""
        print(f"  {rt:<30} {n:>7,}{marker}")

if __name__ == "__main__":
    load_all_bundles()
