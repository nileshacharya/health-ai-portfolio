#!/usr/bin/env python3
"""
Generate demo_data.json for app_demo.py
- Uses hardcoded representative conversations (no DB needed)
- Uses hardcoded SOAP notes (no Claude API needed)
- Runs real attribution logic from attribute_sources_PRODUCTION.py
- Output: demo_data.json ready for Streamlit demo app
"""

import json
import sys
from attribute_sources_PRODUCTION import attribute_sources

# ============================================================================
# REPRESENTATIVE CONVERSATIONS & SOAP NOTES
# 20 cases across SIMPLE / MODERATE / COMPLEX / RARE-EDGE
# ============================================================================

CASES = [
    # ── SIMPLE ──────────────────────────────────────────────────────────────
    {
        "conversation_id": "0U15DA7ozgp2",
        "sample_name": "Sleep Apnea",
        "category": "SIMPLE",
        "complexity_score": 22.4,
        "description": "Patient presenting with excessive daytime sleepiness and snoring.",
        "conversation": """CLINICIAN: What brings you in today?
PATIENT: I've been really tired during the day. My wife says I snore loudly at night and sometimes stop breathing.
CLINICIAN: How long has this been going on?
PATIENT: About a year now. I wake up with headaches and feel like I didn't sleep at all.
CLINICIAN: Do you have any other medical conditions?
PATIENT: I have high blood pressure. I'm on lisinopril.
CLINICIAN: Any chest pain, shortness of breath during the day?
PATIENT: No chest pain. Sometimes short of breath when I climb stairs.
CLINICIAN: Based on your symptoms, I'm concerned about sleep apnea. We'll order a sleep study.
PATIENT: Okay, what does that involve?""",
        "soap_note": """SUBJECTIVE:
Patient presents with a chief complaint of excessive daytime sleepiness persisting for approximately one year. Spouse reports loud snoring and witnessed apneic episodes during sleep. Patient wakes with morning headaches and non-restorative sleep. Past medical history significant for hypertension, currently managed with lisinopril. Patient denies chest pain. Reports mild dyspnea on exertion with stair climbing.

OBJECTIVE:
Vital signs not documented in this encounter. Physical examination findings not detailed in conversation. Patient appears fatigued per clinical impression. No acute distress noted. Cardiopulmonary examination not documented. Weight and BMI not recorded in this visit.

ASSESSMENT:
Clinical presentation consistent with obstructive sleep apnea based on the triad of excessive daytime sleepiness, witnessed apneic episodes, and loud snoring. Morning headaches support nocturnal hypoxemia. Comorbid hypertension may be exacerbated by untreated sleep apnea. Exertional dyspnea warrants monitoring but not primary concern at this time.

PLAN:
Polysomnography (sleep study) ordered to confirm diagnosis of sleep apnea and assess severity. Continue current antihypertensive regimen with lisinopril. Patient educated on sleep apnea and the purpose of sleep study. Follow-up appointment to review sleep study results and discuss treatment options including CPAP therapy. Activity restrictions not indicated at this time."""
    },
    {
        "conversation_id": "CN4XhgsJj8UU",
        "sample_name": "Possible Spider Bite",
        "category": "SIMPLE",
        "complexity_score": 28.0,
        "description": "Patient with swelling and redness at a suspected spider bite site on the arm.",
        "conversation": """CLINICIAN: Tell me what happened.
PATIENT: I woke up two days ago with this red swollen area on my arm. I think a spider bit me while I was sleeping.
CLINICIAN: Any fever or chills?
PATIENT: I had a low-grade fever yesterday, around 100 degrees. No chills.
CLINICIAN: Any spreading redness, red streaks, or pus?
PATIENT: The redness is spreading a little. No pus yet but it's getting more swollen.
CLINICIAN: Any nausea, vomiting, muscle pain?
PATIENT: Some nausea but no vomiting. My arm is aching.
CLINICIAN: Are you on any medications?
PATIENT: Just ibuprofen for the pain and swelling. Taking aspirin sometimes too.
CLINICIAN: I'm going to examine the area. This looks like a local infection. I'll prescribe an antibiotic.
PATIENT: Should I be worried about it being a brown recluse?""",
        "soap_note": """SUBJECTIVE:
Patient presents with a two-day history of a swollen, erythematous lesion on the arm, suspected spider bite occurring during sleep. Associated symptoms include low-grade fever of 100°F documented yesterday, progressive spreading erythema, increasing swelling, nausea without emesis, and localized arm pain. Denies purulent discharge, chills, red streaking. Current medications include ibuprofen for analgesia and aspirin on an as-needed basis. No known drug allergies documented.

OBJECTIVE:
Physical examination reveals erythematous, swollen lesion on the arm with spreading erythema noted on inspection. No frank purulence observed at examination. Low-grade fever documented by history. Vital signs beyond fever temperature not fully documented in this encounter. Lymph node examination, full skin survey, and neurovascular assessment of the affected extremity not documented.

ASSESSMENT:
Presentation consistent with local soft tissue infection, likely secondary to insect or spider bite with secondary bacterial superinfection. Spreading erythema and progressive swelling indicate early cellulitis. Differential includes brown recluse spider envenomation given the patient's concern, though necrotic changes not yet evident. Constitutional symptoms of fever and nausea support systemic inflammatory response.

PLAN:
Antibiotic therapy prescribed for cellulitis — specific agent, dose, and duration to be determined based on clinical judgment and local resistance patterns. Continue ibuprofen for pain and anti-inflammatory effect. Patient instructed to monitor for worsening erythema, development of necrosis, high fever, or red streaking requiring immediate return. Follow-up in 48 to 72 hours to reassess treatment response. Brown recluse envenomation discussed with patient."""
    },
    {
        "conversation_id": "S0hRoqZCct2O",
        "sample_name": "Trouble Breathing",
        "category": "SIMPLE",
        "complexity_score": 40.8,
        "description": "History and physical for a 69-year-old male with difficulty breathing for 3 days.",
        "conversation": """CLINICIAN: What brings you in today?
PATIENT: I have had trouble breathing for the past 3 days.
CLINICIAN: Can you describe the breathing difficulty?
PATIENT: It's hard to catch my breath, especially when I walk or climb stairs. It's worse when I lie down flat.
CLINICIAN: Any cough?
PATIENT: Yes, a dry cough mostly. Sometimes I cough up a little bit of white phlegm.
CLINICIAN: Any chest pain, fever, or swelling in the legs?
PATIENT: No fever. My ankles have been swollen for a few days. No chest pain.
CLINICIAN: Do you have any history of heart or lung problems?
PATIENT: I had a heart attack about 5 years ago. I'm on aspirin and metoprolol. I also have high blood pressure.
CLINICIAN: I'm going to examine you. Let me listen to your lungs and heart.
[Physical examination performed]
CLINICIAN: Your lungs have some crackles at the bases. Your legs are swollen. Given your history, this may be heart failure. We'll get a chest X-ray and some labs.
PATIENT: Is it serious?""",
        "soap_note": """SUBJECTIVE:
Patient is a 69-year-old male presenting with a 3-day history of progressive dyspnea on exertion and orthopnea. Reports difficulty breathing with ambulation and stair climbing, worsening when supine. Associated dry cough with occasional white sputum production. Bilateral ankle swelling noted for several days. Denies chest pain and fever. Significant past medical history includes myocardial infarction approximately 5 years prior and hypertension. Current medications include aspirin and metoprolol.

OBJECTIVE:
Pulmonary auscultation reveals bibasilar crackles. Bilateral lower extremity edema present on examination. Vital signs not fully documented in this encounter. Cardiac examination findings beyond abnormal lung sounds not detailed. Chest X-ray ordered — results pending. Laboratory studies ordered — results pending.

ASSESSMENT:
Clinical presentation strongly consistent with acute decompensated heart failure given the history of prior myocardial infarction, progressive dyspnea on exertion, orthopnea, bibasilar crackles, and bilateral lower extremity edema. Hypertension is a contributing comorbidity. Differential includes pulmonary embolism and pneumonia, though fever absence and bilateral symmetric findings favor heart failure.

PLAN:
Chest X-ray obtained to assess for cardiomegaly and pulmonary edema. Laboratory studies ordered including BNP, complete metabolic panel, and CBC. Continue aspirin and metoprolol. Diuretic therapy to be initiated pending confirmation of heart failure diagnosis. Patient education provided regarding diagnosis, fluid restriction, and daily weight monitoring. Cardiology referral to be considered based on workup results. Close follow-up arranged."""
    },
    {
        "conversation_id": "u7qOicVQWbsj",
        "sample_name": "Thrombocytopenia - SOAP Note",
        "category": "MODERATE",
        "complexity_score": 42.8,
        "description": "Follow-up for patient with low platelet count and easy bruising.",
        "conversation": """CLINICIAN: How have you been feeling since your last visit?
PATIENT: Still getting these bruises easily. And I noticed some small red dots on my legs.
CLINICIAN: Any bleeding from gums, nose, or blood in urine or stool?
PATIENT: My gums bled a little when I brushed my teeth yesterday. No blood in urine or stool.
CLINICIAN: Any fatigue or weakness?
PATIENT: Yes, I've been very fatigued. Weakness too.
CLINICIAN: Your last CBC showed platelets at 45,000. Any new medications or supplements?
PATIENT: I started taking ibuprofen about a month ago for my arthritis pain.
CLINICIAN: Any recent infections or illnesses?
PATIENT: I had a viral infection about 6 weeks ago. Felt like the flu.
CLINICIAN: We need to recheck your platelets and review possible causes. Ibuprofen can affect platelets and we may need to stop it.
PATIENT: Is this dangerous?""",
        "soap_note": """SUBJECTIVE:
Patient presents for follow-up of known thrombocytopenia with persistent easy bruising and new petechiae on bilateral lower extremities. Reports gingival bleeding with tooth brushing. Denies hematuria or melena. Associated symptoms include significant fatigue and weakness. Recent history significant for viral illness resembling influenza approximately 6 weeks prior. Medication review reveals recent addition of ibuprofen approximately one month ago for arthritis pain management. Prior platelet count documented at 45,000.

OBJECTIVE:
Physical examination reveals petechiae on bilateral lower extremities and easy bruising. Gingival bleeding reported by patient. Vital signs not documented in this encounter. Complete blood count with platelets ordered to reassess thrombocytopenia. Additional laboratory evaluation pending. Splenomegaly assessment not documented in this visit.

ASSESSMENT:
Thrombocytopenia with worsening clinical manifestations including petechiae and mucosal bleeding. Differential diagnosis includes drug-induced thrombocytopenia secondary to ibuprofen use, post-viral immune thrombocytopenia following recent influenza-like illness, and immune thrombocytopenic purpura. The temporal relationship between ibuprofen initiation and symptom progression warrants medication discontinuation as initial intervention.

PLAN:
Discontinue ibuprofen immediately given potential contribution to thrombocytopenia. Repeat CBC with differential and platelet count. Consider peripheral blood smear review. Alternative analgesia for arthritis to be discussed — acetaminophen preferred given platelet concerns. Hematology referral to be placed if platelet count does not improve or continues to decline. Patient educated on bleeding precautions and signs requiring emergency evaluation including severe bleeding or neurological symptoms. Follow-up in one week."""
    },
    {
        "conversation_id": "B3YKBkDgcBnT",
        "sample_name": "Normal Male Exam Template - 2",
        "category": "MODERATE",
        "complexity_score": 44.0,
        "description": "Annual physical exam for a middle-aged male with multiple chronic conditions.",
        "conversation": """CLINICIAN: You're here for your annual physical. How have you been overall?
PATIENT: Pretty good. Managing my diabetes and blood pressure okay. Taking metformin and lisinopril.
CLINICIAN: Any new symptoms? Chest pain, shortness of breath?
PATIENT: Occasional shortness of breath going up stairs. No chest pain.
CLINICIAN: How about your weight? Any changes?
PATIENT: Gained about 10 pounds in the last year. I know I need to work on my diet.
CLINICIAN: Any abdominal pain, changes in bowel habits?
PATIENT: No abdominal pain. Maybe a little constipation lately.
CLINICIAN: Sleep okay? Mood?
PATIENT: Sleep is fine. Mood is good, no depression or anxiety.
CLINICIAN: Let me do a complete physical exam.
[Full physical examination performed]
CLINICIAN: Your blood pressure is slightly elevated today. Heart and lungs sound normal. Abdomen is soft. We'll get your routine labs — HbA1c, lipid panel, and CBC.
PATIENT: Should I adjust my medications?""",
        "soap_note": """SUBJECTIVE:
Patient presents for annual physical examination. Reports overall stable health with active management of known diabetes mellitus and hypertension. Current medications include metformin for glycemic control and lisinopril for blood pressure management. Reports mild dyspnea on exertion with stair climbing. Denies chest pain. Notes approximately 10-pound weight gain over the past year with acknowledged dietary indiscretion. Mild constipation reported without abdominal pain, rectal bleeding, or change in stool caliber. Denies depressive symptoms or anxiety. Sleep reported as satisfactory.

OBJECTIVE:
Blood pressure elevated above target range on today's measurement — specific values not documented. Cardiac auscultation normal without murmurs, rubs, or gallops. Pulmonary auscultation clear to auscultation bilaterally. Abdomen soft, non-tender, non-distended. Weight increased approximately 10 pounds from prior visit. Complete physical examination performed. Laboratory studies ordered including HbA1c, lipid panel, and CBC.

ASSESSMENT:
Diabetes mellitus on metformin — glycemic control to be assessed with HbA1c results. Hypertension with suboptimal blood pressure control on current regimen — medication adjustment may be warranted. Weight gain of 10 pounds over one year consistent with metabolic risk progression. Exertional dyspnea likely related to deconditioning and weight gain rather than primary cardiopulmonary pathology, though requires monitoring. Constipation — likely dietary, low clinical concern at this time.

PLAN:
Laboratory studies ordered: HbA1c, comprehensive lipid panel, CBC with differential. Blood pressure management to be reassessed following laboratory review — consider lisinopril dose increase if HbA1c and renal function support. Dietary counseling and physical activity recommendations provided. Weight loss goal discussed with patient. Constipation managed with dietary fiber increase and hydration. Follow-up in 3 months or sooner if blood pressure concern warrants earlier review. Screening colonoscopy discussion deferred to next visit."""
    },

    # ── MODERATE ────────────────────────────────────────────────────────────
    {
        "conversation_id": "CEDgXx9DgFbC",
        "sample_name": "Obesity Hypoventilation Syndrome",
        "category": "RARE/EDGE",
        "complexity_score": 52.8,
        "description": "Morbidly obese patient with daytime hypercapnia and respiratory failure.",
        "conversation": """CLINICIAN: You were referred for evaluation of breathing problems. Tell me about your symptoms.
PATIENT: I get very short of breath doing almost anything. Even sitting, sometimes.
CLINICIAN: Any swelling in your legs?
PATIENT: Yes, bad swelling in both legs. And I feel confused sometimes in the mornings.
CLINICIAN: Do you use any breathing device at night?
PATIENT: I was told to use a CPAP but I don't tolerate it well.
CLINICIAN: Your ABG shows CO2 of 58. Do you know your weight?
PATIENT: About 380 pounds. I've always been heavy.
CLINICIAN: Any history of heart problems?
PATIENT: They said I have pulmonary hypertension. And my heart is enlarged.
CLINICIAN: How is your sleep? Do you feel rested?
PATIENT: Never rested. I fall asleep during the day constantly. My wife says I stop breathing at night.
CLINICIAN: We need to address your ventilation urgently. I'm recommending BiPAP and a pulmonology referral.
PATIENT: Is this from my weight?""",
        "soap_note": """SUBJECTIVE:
Patient presents with severe dyspnea occurring with minimal exertion and at rest. Associated symptoms include bilateral lower extremity edema, morning confusion, and excessive daytime sleepiness with witnessed apneic episodes reported by spouse. Patient reports poor tolerance of prescribed CPAP therapy. Arterial blood gas demonstrates hypercapnia with CO2 of 58 mmHg, consistent with chronic hypoventilation. Body weight approximately 380 pounds with longstanding morbid obesity. Known history of pulmonary hypertension and cardiomegaly. Non-restorative sleep pattern with daytime somnolence.

OBJECTIVE:
Morbid obesity with body weight approximately 380 pounds. ABG results significant for CO2 of 58 mmHg indicating hypercapnia. Bilateral lower extremity edema present on examination. Pulmonary hypertension and cardiomegaly per prior diagnostic evaluation. Oxygen saturation, respiratory rate, and full vital signs not documented in this encounter. Pulmonary function testing results not available at this visit. Echocardiogram findings not detailed.

ASSESSMENT:
Obesity hypoventilation syndrome with chronic hypercapnic respiratory failure, evidenced by morbid obesity, daytime CO2 retention of 58 mmHg, excessive daytime sleepiness, and witnessed apneic events. Comorbid pulmonary hypertension and cardiomegaly indicate end-organ impact from chronic hypoxemia and hypercapnia. Obstructive sleep apnea component suspected given CPAP prescription history. Morning confusion suggests recurrent nocturnal hypercapnic episodes.

PLAN:
Transition from CPAP to BiPAP to improve ventilatory support given documented hypercapnia and CPAP intolerance. Urgent pulmonology referral placed for comprehensive respiratory management. Cardiology involvement for pulmonary hypertension and cardiomegaly management. Weight loss intervention — bariatric surgery evaluation to be discussed given severity of obesity-related comorbidities. Patient education on the relationship between obesity and respiratory failure. Sleep study (polysomnography with CO2 monitoring) to be ordered. Close monitoring of ABG and clinical status."""
    },
    {
        "conversation_id": "Y9BsOifbX6cR",
        "sample_name": "Recurrent Abscesses - Consult",
        "category": "MODERATE",
        "complexity_score": 54.8,
        "description": "Patient with recurrent skin abscesses and possible underlying immune deficiency.",
        "conversation": """CLINICIAN: Tell me about these recurring infections.
PATIENT: I've had abscesses popping up all over — armpits, groin, under my breasts. This has been going on for two years.
CLINICIAN: How often do they occur?
PATIENT: About once a month. They get really painful and sometimes drain on their own.
CLINICIAN: Have you been hospitalized for any of them?
PATIENT: Twice. They gave me IV antibiotics both times.
CLINICIAN: Any fever with the abscesses?
PATIENT: Yes, I get fever and chills when they get bad.
CLINICIAN: Any family history of similar skin conditions or immune problems?
PATIENT: My mother had similar skin problems.
CLINICIAN: Do you have diabetes or any autoimmune conditions?
PATIENT: No diabetes. I was told I might have hidradenitis suppurativa.
CLINICIAN: Based on your history and distribution, I agree with that diagnosis. We also need to rule out an underlying immune deficiency given the severity.
PATIENT: What causes this?""",
        "soap_note": """SUBJECTIVE:
Patient presents for consultation regarding a 2-year history of recurrent painful abscesses involving bilateral axillae, inguinal regions, and inframammary folds. Episodes occur approximately monthly with associated fever and chills during severe flares. Two prior hospitalizations required for intravenous antibiotic therapy. Lesions occasionally undergo spontaneous drainage. Family history significant for similar cutaneous condition in mother. No known diagnosis of diabetes or autoimmune disease. Prior clinical impression of hidradenitis suppurativa noted.

OBJECTIVE:
Physical examination reveals characteristic distribution of abscesses and scarring involving axillae, inguinal regions, and inframammary areas consistent with Hurley staging of hidradenitis suppurativa. Active lesion assessment and Hurley stage not documented in this note. Vital signs not recorded. Laboratory evaluation for immune deficiency not yet resulted. Dermatology examination details not fully documented.

ASSESSMENT:
Hidradenitis suppurativa with recurrent severe flares requiring hospitalization, consistent with moderate-to-severe disease classification. Characteristic anatomical distribution involving intertriginous areas supports this diagnosis. Family history suggests possible genetic predisposition. Frequency and severity of episodes raise concern for underlying immune deficiency or immunomodulatory disorder warranting further investigation.

PLAN:
Confirm hidradenitis suppurativa diagnosis and perform Hurley staging to guide treatment intensity. Immune deficiency workup including immunoglobulin levels, CBC with differential, and complement levels. Referral to dermatology for specialist management — consideration of biologics (adalimumab is FDA-approved for moderate-to-severe HS). Wound care guidance for active lesions. Antibiotic therapy for current flare. Lifestyle modifications discussed including smoking cessation if applicable and weight management. Genetic counseling consideration given family history."""
    },
    {
        "conversation_id": "bLiHoeCVVrjp",
        "sample_name": "Normal Physical Exam Template - 5",
        "category": "MODERATE",
        "complexity_score": 56.0,
        "description": "Comprehensive annual exam with multiple system review and chronic disease management.",
        "conversation": """CLINICIAN: Let's go through your systems today for your annual exam.
PATIENT: Sure. I've been managing okay but I have a few concerns.
CLINICIAN: Let's start from the top. Any headaches, vision changes, dizziness?
PATIENT: Some headaches lately. No vision changes. Occasional dizziness when I stand up fast.
CLINICIAN: Chest or heart symptoms?
PATIENT: I have my usual heart palpitations. My cardiologist knows about them.
CLINICIAN: Breathing okay?
PATIENT: I use my inhaler sometimes for my asthma. Better controlled lately.
CLINICIAN: Stomach, bowel, bladder?
PATIENT: Some acid reflux. Taking omeprazole for it. Bowels normal.
CLINICIAN: Joints, muscles?
PATIENT: Arthritis in my knees. Some pain and stiffness in the mornings.
CLINICIAN: Mood, sleep, energy?
PATIENT: I've been feeling a bit depressed lately. Sleep is poor. Energy is low.
CLINICIAN: Any numbness, tingling, memory issues?
PATIENT: Some tingling in my feet. I'm a diabetic so my doctor watches that.
CLINICIAN: Let me examine you fully.
[Full physical examination performed]""",
        "soap_note": """SUBJECTIVE:
Patient presents for comprehensive annual physical examination with multiple active concerns. Neurological: reports recent onset headaches and orthostatic dizziness without syncope; denies vision changes. Cardiovascular: known palpitations under active cardiology follow-up. Pulmonary: asthma with improved control on current inhaler regimen. Gastrointestinal: gastroesophageal reflux disease managed with omeprazole; normal bowel habits. Musculoskeletal: bilateral knee osteoarthritis with morning stiffness and pain. Psychiatric: new depressive symptoms with poor sleep and low energy. Neurological: bilateral foot tingling in context of known diabetes mellitus, concerning for peripheral neuropathy.

OBJECTIVE:
Comprehensive physical examination performed. Findings not individually detailed in this encounter note. Vital signs including orthostatic blood pressures not documented. Neurological examination of lower extremities including monofilament testing not documented. Cardiac rhythm assessment not documented given palpitation history.

ASSESSMENT:
Multiple active chronic conditions requiring coordinated management: diabetes mellitus with possible early peripheral neuropathy (bilateral foot tingling), asthma currently well-controlled, gastroesophageal reflux disease on proton pump inhibitor, bilateral knee osteoarthritis, cardiac arrhythmia under cardiology care, and new depressive symptoms warranting formal assessment. Orthostatic dizziness may represent autonomic neuropathy component or medication side effect.

PLAN:
Diabetes management: HbA1c, renal function, urine microalbumin, monofilament foot exam — peripheral neuropathy evaluation. Depression screening with PHQ-9; initiate treatment or refer to psychiatry based on severity. Asthma: continue current inhaler, confirm written asthma action plan. GERD: continue omeprazole, reinforce dietary modifications. Osteoarthritis: optimize analgesia, physical therapy referral. Palpitations: cardiology follow-up confirmed. Orthostatic dizziness: orthostatic vital sign measurement at next visit. Complete metabolic panel and lipid panel ordered."""
    },
    {
        "conversation_id": "Ixe2I3lrKFYK",
        "sample_name": "Pain from Hernia - ER Consult",
        "category": "RARE/EDGE",
        "complexity_score": 57.6,
        "description": "ER consult for acute groin pain with suspected incarcerated hernia.",
        "conversation": """CLINICIAN: Tell me about your pain.
PATIENT: I have severe pain in my right groin. Started a few hours ago and it's getting worse.
CLINICIAN: Do you have a history of hernia?
PATIENT: Yes, I was told I had a right inguinal hernia a few years ago but never had surgery.
CLINICIAN: Any nausea, vomiting?
PATIENT: Yes, I've been nauseous and vomited twice.
CLINICIAN: Any fever?
PATIENT: I feel warm. Not sure if I have a fever.
CLINICIAN: Any change in bowel movements or gas?
PATIENT: I haven't been able to pass gas since this morning. No bowel movement either.
CLINICIAN: Can I examine your groin?
[Examination performed]
CLINICIAN: There's a tender, irreducible mass in your right inguinal region. I'm very concerned about an incarcerated hernia. We need surgical consultation immediately.
PATIENT: Do I need surgery tonight?""",
        "soap_note": """SUBJECTIVE:
Patient presents to the emergency department with acute severe right groin pain with onset several hours prior and progressive worsening. Known history of right inguinal hernia diagnosed several years ago without prior surgical repair. Associated symptoms include nausea, two episodes of emesis, subjective fever, inability to pass flatus since morning, and absence of bowel movement. No prior similar episodes documented.

OBJECTIVE:
Physical examination reveals tender, irreducible mass in the right inguinal region consistent with incarcerated inguinal hernia. Bowel sounds assessment not documented. Abdominal examination findings not detailed beyond groin mass. Temperature documented as subjectively elevated — specific value not recorded. Full vital signs not documented in this note. Imaging studies not yet resulted at time of this note.

ASSESSMENT:
Acute incarcerated right inguinal hernia with high concern for strangulation given irreducibility, severe pain, and associated obstructive symptoms including inability to pass flatus and vomiting. This represents a surgical emergency. Bowel obstruction cannot be excluded. Strangulation with bowel ischemia is the primary concern requiring urgent operative intervention.

PLAN:
Immediate surgical consultation placed — emergency surgical evaluation for incarcerated hernia with possible strangulation. IV access established, NPO status implemented, IV fluids initiated. Analgesia administered. Urgent CT abdomen and pelvis with contrast ordered to assess hernia contents and viability. Surgical repair likely required on emergent basis tonight. Patient and family counseled on diagnosis, urgency, and surgical risk. Anesthesia notification pending surgical decision."""
    },
    {
        "conversation_id": "Xs4GRIFhjHJT",
        "sample_name": "Normal Newborn H&P Template",
        "category": "MODERATE",
        "complexity_score": 58.8,
        "description": "Newborn well-baby examination and history including birth details and feeding.",
        "conversation": """CLINICIAN: Congratulations on your new baby. Let me go through the birth history and examine the baby.
PARENT: Thank you. The birth went well but we're worried about the jaundice.
CLINICIAN: Tell me about the delivery.
PARENT: She was born at 39 weeks by vaginal delivery. Birth weight was 7 pounds 4 ounces. Apgar scores were 8 and 9.
CLINICIAN: Any complications during pregnancy or delivery?
PARENT: No complications. Group B strep was negative.
CLINICIAN: How is she feeding?
PARENT: Breastfeeding. Latching well and feeding every 2 to 3 hours.
CLINICIAN: Any jaundice concerns?
PARENT: She looks a bit yellow. Started yesterday at day 2 of life.
CLINICIAN: How many wet diapers and stools?
PARENT: About 4 wet diapers and 2-3 yellow stools per day.
CLINICIAN: Let me examine her fully.
[Newborn physical examination performed]
CLINICIAN: She has mild physiologic jaundice. We'll check a bilirubin level. Everything else looks normal on exam.
PARENT: When do we need to worry?""",
        "soap_note": """SUBJECTIVE:
Well-baby examination for a female newborn at day 2 of life. Birth history: gestational age 39 weeks, vaginal delivery, birth weight 7 pounds 4 ounces, Apgar scores 8 at one minute and 9 at five minutes. No perinatal complications. Group B Streptococcus screen negative. Breastfeeding initiated with good latch and feeding every 2-3 hours. Urine output adequate with approximately 4 wet diapers per day. Stooling pattern normal with 2-3 yellow stools daily. Parent notes mild icterus onset at day 2 of life — clinical concern for neonatal jaundice.

OBJECTIVE:
Newborn physical examination performed. Mild icterus noted on skin inspection. Weight, head circumference, and length not documented in this note. Vital signs including temperature and respiratory rate not recorded. Cardiac, pulmonary, abdominal, neurological, and musculoskeletal examinations performed — findings reported as normal. Total serum bilirubin ordered — results pending.

ASSESSMENT:
Physiologic neonatal jaundice at day 2 of life — timing and clinical presentation consistent with physiologic rather than pathologic etiology. Adequate feeding and stooling support benign course. Risk stratification pending bilirubin level. Group B Strep negative maternal status reduces infection concern. Overall newborn examination within normal limits.

PLAN:
Total serum bilirubin measurement to determine phototherapy threshold based on Bhutani nomogram and gestational age. Parent education on jaundice progression, monitoring for worsening icterus extending to extremities, decreased feeding, or lethargy. Continue breastfeeding support — lactation consultation offered. Follow-up in 24-48 hours for repeat bilirubin and weight check. Newborn screening (state metabolic screen and hearing screen) to be completed prior to discharge. Return precautions provided."""
    },

    # ── COMPLEX ─────────────────────────────────────────────────────────────
    {
        "conversation_id": "2qeiMvG87y1M",
        "sample_name": "Tongue Swelling",
        "category": "COMPLEX",
        "complexity_score": 72.4,
        "description": "Acute angioedema of the tongue with airway compromise concern.",
        "conversation": """CLINICIAN: How long has your tongue been swollen?
PATIENT: About two hours. It started suddenly.
CLINICIAN: Any difficulty breathing or swallowing?
PATIENT: It's getting hard to swallow. A little hard to breathe.
CLINICIAN: Any hives or rash on your body?
PATIENT: Some hives on my arms and chest.
CLINICIAN: Any recent new medications or foods?
PATIENT: I just started lisinopril two weeks ago for blood pressure.
CLINICIAN: Any history of allergies or previous angioedema?
PATIENT: No history of angioedema. Allergic to penicillin.
CLINICIAN: Any throat tightness or change in voice?
PATIENT: My voice sounds different. Throat feels tight.
CLINICIAN: This is a serious reaction. I'm calling the team now.
[Emergency team activated]
CLINICIAN: We're going to give you epinephrine and antihistamines and monitor your airway closely. An ENT and anesthesia are being called.
PATIENT: Am I going to be okay?""",
        "soap_note": """SUBJECTIVE:
Patient presents with acute onset tongue swelling of approximately 2 hours duration with progressive worsening. Associated symptoms include dysphagia, mild dyspnea, voice change, throat tightness, and urticaria on bilateral upper extremities and chest. Recent medication initiation: lisinopril started 2 weeks prior for hypertension management. Known drug allergy: penicillin. No prior history of angioedema. No new foods or other exposures identified.

OBJECTIVE:
Visible macroglossia on oral examination with progressive tongue edema. Urticarial lesions on bilateral arms and chest. Voice change audible consistent with supraglottic edema. Respiratory assessment shows mild dyspnea — oxygen saturation not documented in this note. Airway patency currently maintained but under active monitoring. Emergency team activated. ENT and anesthesia consultations placed. IV access established.

ASSESSMENT:
ACE inhibitor-induced angioedema secondary to lisinopril, presenting with acute tongue and likely supraglottic edema with urticaria. This represents a potentially life-threatening airway emergency. ACE inhibitor angioedema is characteristically non-histaminergic and bradykinin-mediated, which limits response to epinephrine and antihistamines compared to allergic angioedema, though these are administered empirically. Airway compromise is the primary immediate concern.

PLAN:
Immediate interventions: epinephrine administered, antihistamine (diphenhydramine) and corticosteroid (methylprednisolone) IV initiated. Discontinue lisinopril permanently — ACE inhibitor class contraindicated. Airway monitoring with anesthesia and ENT at bedside for potential emergent intubation or surgical airway. Supplemental oxygen applied. Consider icatibant or fresh frozen plasma if angioedema refractory to initial management. Admission to monitored setting. Patient counseled on ACE inhibitor avoidance. Alternative antihypertensive class (ARB used with caution, calcium channel blocker preferred) to be arranged on discharge."""
    },
    {
        "conversation_id": "Win8pvy0nQpc",
        "sample_name": "Airway Compromise & Foreign Body - ER Visit",
        "category": "COMPLEX",
        "complexity_score": 74.4,
        "description": "Child presenting to ER with suspected foreign body aspiration and respiratory distress.",
        "conversation": """CLINICIAN: What happened?
PARENT: He was eating peanuts and then started coughing and choking. He's been having trouble breathing for an hour.
CLINICIAN: How old is he?
PARENT: Three years old.
CLINICIAN: Is he able to breathe right now?
PARENT: He's breathing but it sounds wheezy. He keeps coughing.
CLINICIAN: Any fever?
PARENT: No fever.
CLINICIAN: Any history of asthma or previous breathing problems?
PARENT: No, he's been healthy. No asthma.
CLINICIAN: Let me examine him.
[Examination performed]
CLINICIAN: I can hear decreased breath sounds on the right. His oxygen saturation is 93%. This is consistent with a foreign body in the right bronchus. We need a chest X-ray and urgent pediatric pulmonology for bronchoscopy.
PARENT: Can you get it out?
CLINICIAN: Yes, through a bronchoscopy procedure. We're activating the team now.
PARENT: Is this dangerous?""",
        "soap_note": """SUBJECTIVE:
A 3-year-old male presents to the emergency department following acute onset choking episode while eating peanuts approximately one hour prior to presentation. Witnessed aspiration event by parent. Persistent cough and wheeze since episode onset. Increasing respiratory distress reported. Denies fever. No prior history of asthma or respiratory illness. Previously healthy child with no significant past medical history.

OBJECTIVE:
Oxygen saturation 93% on room air. Pulmonary auscultation reveals decreased breath sounds on the right side with expiratory wheeze. No stridor documented. Respiratory rate elevated — specific value not documented. Work of breathing assessment not detailed. Chest X-ray ordered — results pending. Pediatric pulmonology consultation activated for urgent bronchoscopy evaluation.

ASSESSMENT:
Foreign body aspiration with right bronchial obstruction in a 3-year-old child, evidenced by witnessed aspiration event, unilateral decreased breath sounds on the right, expiratory wheeze, and oxygen desaturation to 93%. Peanut aspiration is the most likely foreign body given clear history. Right bronchus involvement consistent with anatomical predisposition. This represents a respiratory emergency requiring urgent bronchoscopic retrieval.

PLAN:
Urgent rigid bronchoscopy for foreign body retrieval — pediatric pulmonology and pediatric surgery notified. Supplemental oxygen applied with target saturation above 95%. IV access established. NPO status implemented for procedural preparation. Chest X-ray to assess for hyperinflation, atelectasis, or mediastinal shift. Anesthesia consultation for procedural sedation. Continuous cardiorespiratory monitoring. Parent counseled on diagnosis, procedure, and risks. ICU post-procedure monitoring to be arranged."""
    },
    {
        "conversation_id": "Chp9WGwltx0p",
        "sample_name": "Normal ROS Template - 4",
        "category": "COMPLEX",
        "complexity_score": 77.2,
        "description": "Comprehensive multi-system review of systems with extensive symptom inventory.",
        "conversation": """CLINICIAN: I need to go through a complete review of systems today.
PATIENT: Okay, I'll try to answer everything.
CLINICIAN: Constitutional — any fever, chills, weight loss, fatigue, night sweats?
PATIENT: Some fatigue. Night sweats for the past month. No fever or weight loss.
CLINICIAN: Head, eyes, ears, nose, throat?
PATIENT: Headaches weekly. Vision blurry sometimes. No hearing problems. Some sinus congestion.
CLINICIAN: Cardiovascular?
PATIENT: Occasional chest pain — dull, not severe. Heart racing sometimes. Leg swelling on and off.
CLINICIAN: Respiratory?
PATIENT: Shortness of breath with exercise. Morning cough sometimes. No wheezing.
CLINICIAN: Gastrointestinal?
PATIENT: Nausea occasionally. Diarrhea a few times a week. Some abdominal pain after eating.
CLINICIAN: Genitourinary?
PATIENT: Frequent urination. Some burning with urination.
CLINICIAN: Musculoskeletal?
PATIENT: Joint pain in hands and knees. Morning stiffness lasting over an hour.
CLINICIAN: Neurological?
PATIENT: Numbness in both hands. Occasional dizziness. Memory seems worse lately.
CLINICIAN: Psychiatric?
PATIENT: Feeling anxious and depressed. Sleep is very disrupted.
CLINICIAN: Skin?
PATIENT: A new rash on my arms — red and itchy. Some hair loss.
CLINICIAN: Endocrine?
PATIENT: Always thirsty and urinating a lot. Feeling cold all the time.
CLINICIAN: Hematologic?
PATIENT: Easy bruising lately. Some bleeding from gums.""",
        "soap_note": """SUBJECTIVE:
Comprehensive review of systems reveals multi-system involvement. Constitutional: fatigue and night sweats for one month without documented fever, chills, or weight loss. HEENT: weekly headaches, intermittent blurry vision, sinus congestion; no hearing impairment. Cardiovascular: dull non-severe chest pain, palpitations, intermittent bilateral lower extremity edema. Pulmonary: exertional dyspnea, morning cough without wheeze. Gastrointestinal: nausea, diarrhea several times weekly, postprandial abdominal pain. Genitourinary: urinary frequency and dysuria. Musculoskeletal: bilateral hand and knee arthralgia with prolonged morning stiffness exceeding one hour. Neurological: bilateral hand paresthesias, dizziness, cognitive complaints. Psychiatric: anxiety, depression, and sleep disturbance. Dermatologic: pruritic erythematous arm rash and alopecia. Endocrine: polydipsia and polyuria with cold intolerance. Hematologic: easy bruising and gingival bleeding.

OBJECTIVE:
Physical examination not documented in this encounter. Vital signs not recorded. Multi-system examination warranted given extensive symptom inventory but findings not detailed. Laboratory evaluation to be ordered based on symptom clusters.

ASSESSMENT:
Extensive multi-system symptom complex requiring systematic evaluation. Key diagnostic considerations: polyuria, polydipsia, and fatigue suggest diabetes mellitus; cold intolerance and fatigue raise hypothyroidism concern; prolonged morning stiffness with polyarthralgia suggests inflammatory arthropathy (rheumatoid arthritis); easy bruising and gingival bleeding raise thrombocytopenia concern; rash, alopecia, and multi-system involvement warrant autoimmune evaluation (lupus); night sweats, fatigue, and cognitive changes require malignancy exclusion.

PLAN:
Comprehensive laboratory workup: CBC with differential, CMP, HbA1c, fasting glucose, thyroid panel (TSH/free T4), rheumatoid factor, anti-CCP, ANA with reflex, anti-dsDNA, complement levels, urinalysis with culture. Imaging: chest X-ray for pulmonary symptoms. Subspecialty referrals based on laboratory results: rheumatology, endocrinology, hematology as indicated. Follow-up in 1-2 weeks for laboratory review. Patient counseled on broad differential and the need for systematic evaluation."""
    },
    {
        "conversation_id": "q5dVhK86R6je",
        "sample_name": "Normal Physical Exam Template - 7",
        "category": "RARE/EDGE",
        "complexity_score": 78.4,
        "description": "Complex patient with multi-system disease and extensive physical exam documentation.",
        "conversation": """CLINICIAN: Let me do a complete physical exam. Starting with your vitals and general appearance.
PATIENT: Okay. I've been feeling run down overall.
CLINICIAN: Blood pressure 148 over 92. Heart rate 88. Temperature 98.6. Weight 210 pounds.
PATIENT: My blood pressure is always high. I'm on two medications for it.
CLINICIAN: Let me examine your head and neck. Any lymph node swelling?
PATIENT: I noticed a lump on the left side of my neck last week.
CLINICIAN: Eyes, vision?
PATIENT: I wear glasses. Vision has been blurry lately.
CLINICIAN: Let me listen to your heart and lungs.
[Cardiac and pulmonary exam performed]
CLINICIAN: I hear a murmur — soft, systolic. Your lungs are clear.
PATIENT: I've had that murmur for years. Is it worse?
CLINICIAN: Abdomen exam — any tenderness?
PATIENT: Some tenderness on the right upper side.
CLINICIAN: I feel your liver edge slightly below the rib margin. That's worth investigating.
PATIENT: My last liver tests were slightly off a few months ago.
CLINICIAN: Neurological exam looks intact. Reflexes are normal. Let's talk about the neck lump and liver finding.
PATIENT: Should I be worried?""",
        "soap_note": """SUBJECTIVE:
Patient presents with complaints of generalized fatigue and recent discovery of a left neck mass one week prior. Known history of hypertension currently managed on two antihypertensive medications. History of cardiac murmur. Recent blurry vision in context of corrective lens use. Right upper quadrant abdominal tenderness reported. Prior liver function tests mildly abnormal several months ago without documented follow-up.

OBJECTIVE:
Vital signs: blood pressure 148/92 mmHg indicating uncontrolled hypertension on current regimen, heart rate 88 bpm, temperature 98.6°F, weight 210 pounds. Head and neck: left cervical lymphadenopathy — palpable node, size and character not further detailed. Ophthalmologic: corrective lenses worn, blurry vision reported. Cardiac: soft systolic murmur on auscultation — grade not documented; known history. Pulmonary: clear to auscultation bilaterally. Abdomen: right upper quadrant tenderness with palpable liver edge below costal margin indicating hepatomegaly. Neurological: cranial nerves intact, reflexes normal.

ASSESSMENT:
Multiple findings requiring workup: new left cervical lymphadenopathy in context of fatigue, hepatomegaly, and prior abnormal liver function tests — malignancy including lymphoma must be excluded. Hepatomegaly with right upper quadrant tenderness and known abnormal LFTs warrants hepatic evaluation. Uncontrolled hypertension on dual therapy. Systolic murmur — baseline comparison needed. Blurry vision requires ophthalmologic assessment.

PLAN:
Urgent workup for cervical lymphadenopathy: CBC with differential, LDH, uric acid, peripheral smear; CT neck/chest/abdomen/pelvis with contrast for lymphoma staging evaluation. Liver evaluation: LFTs, hepatitis B and C serologies, abdominal ultrasound. Blood pressure management: review current antihypertensive regimen, consider addition of third agent or dose adjustment. Echocardiogram to assess cardiac murmur. Ophthalmology referral for blurry vision. Follow-up in 1 week to review results — expedited if imaging raises oncologic concern."""
    },
    {
        "conversation_id": "OJJLdMsb4iqO",
        "sample_name": "Refractory Hypertension - Followup",
        "category": "COMPLEX",
        "complexity_score": 80.8,
        "description": "Follow-up for patient with hypertension resistant to multiple medications.",
        "conversation": """CLINICIAN: Your blood pressure is still elevated today — 162 over 98. How have you been with your medications?
PATIENT: I take them every day. Lisinopril, amlodipine, and hydrochlorothiazide.
CLINICIAN: Any chest pain, headache, or vision changes?
PATIENT: Some headaches, especially in the morning. No chest pain. Vision is okay.
CLINICIAN: How about your kidneys? Have you had labs recently?
PATIENT: My creatinine was slightly elevated last time. The doctor said to watch it.
CLINICIAN: Any snoring or sleep problems?
PATIENT: My wife says I snore terribly. I'm always exhausted.
CLINICIAN: Any weight gain?
PATIENT: About 20 pounds over the last two years.
CLINICIAN: Do you drink alcohol?
PATIENT: A few beers on weekends. Maybe 3 or 4.
CLINICIAN: The fact that you're on three medications and your blood pressure is still this high is concerning. We need to look for secondary causes. I'm thinking sleep apnea could be contributing.
PATIENT: What other causes could there be?
CLINICIAN: Kidney artery narrowing, hormone problems like aldosterone excess, thyroid issues. We'll order tests.
PATIENT: I just want it under control.""",
        "soap_note": """SUBJECTIVE:
Patient presents for hypertension follow-up with blood pressure remaining uncontrolled at 162/98 mmHg on maximal triple antihypertensive therapy including lisinopril, amlodipine, and hydrochlorothiazide — meeting criteria for resistant hypertension. Reports full medication compliance. Associated symptoms: morning headaches, chronic fatigue, and witnessed loud snoring by spouse suggestive of obstructive sleep apnea. Denies chest pain and visual disturbance. Recent mild creatinine elevation noted on prior laboratory evaluation without formal nephrology referral. Weight gain of approximately 20 pounds over two years. Alcohol consumption: 3-4 standard drinks on weekends.

OBJECTIVE:
Blood pressure 162/98 mmHg — significantly above target despite triple therapy. Heart rate, temperature, and other vital signs not documented. BMI not calculated but 20-pound weight gain noted. Renal function: creatinine mildly elevated on prior labs — current value not available. Ophthalmoscopic examination for hypertensive retinopathy not documented. Cardiac and pulmonary examination findings not detailed.

ASSESSMENT:
Resistant hypertension defined as uncontrolled blood pressure on three antihypertensive agents including a diuretic. Evaluation for secondary causes indicated: obstructive sleep apnea (witnessed snoring, fatigue, weight gain — most common secondary cause), primary hyperaldosteronism, renal artery stenosis, and thyroid dysfunction. Mild renal impairment may limit ACE inhibitor dosing and warrants nephrology evaluation. Alcohol consumption may be contributing to blood pressure elevation.

PLAN:
Secondary hypertension workup: polysomnography for sleep apnea evaluation; plasma aldosterone to renin ratio; renal artery duplex ultrasound or CT angiography; TSH. Renal function reassessment: BMP with creatinine, urine albumin-to-creatinine ratio. Nephrology referral given resistant hypertension with renal impairment. Alcohol reduction counseling provided. Weight loss intervention. Review antihypertensive regimen pending secondary cause results — spironolactone addition if hyperaldosteronism confirmed. Follow-up in 2-4 weeks with secondary workup results."""
    },
    {
        "conversation_id": "C1ymAgLDI2nF",
        "sample_name": "Shortness Of Breath - Progress Note",
        "category": "COMPLEX",
        "complexity_score": 90.8,
        "description": "Inpatient progress note for hospitalized patient with decompensated heart failure and COPD.",
        "conversation": """CLINICIAN: Good morning. How are you feeling compared to yesterday?
PATIENT: Still short of breath, but maybe slightly better. I slept a little.
CLINICIAN: How much fluid came off overnight with the IV Lasix?
PATIENT: The nurse said about 1.5 liters.
CLINICIAN: Any chest pain? Fever?
PATIENT: No chest pain. No fever since yesterday.
CLINICIAN: You mentioned last night your legs feel less heavy?
PATIENT: Yes, the swelling is a little better in my ankles.
CLINICIAN: Your BNP yesterday was 2400. Troponin was negative. Echo showed EF of 25%.
PATIENT: That sounds serious. Is my heart getting weaker?
CLINICIAN: Your EF is quite reduced. We're also managing your COPD and diabetes.
PATIENT: I'm on a lot of medications. Furosemide, carvedilol, insulin, tiotropium, albuterol.
CLINICIAN: Your oxygen saturation overnight dropped to 88% a few times. We may need to adjust your CPAP settings.
PATIENT: What happens if it doesn't improve?
CLINICIAN: We'll discuss advanced therapies if needed. For now let's focus on getting you stable.
PATIENT: Okay doctor.""",
        "soap_note": """SUBJECTIVE:
Inpatient progress note. Patient reports mild subjective improvement in dyspnea compared to yesterday. Urine output approximately 1.5 liters overnight with IV furosemide therapy. Bilateral lower extremity edema improving per patient report. Denies chest pain and fever since yesterday. Sleep slightly improved. Current medications: furosemide IV, carvedilol, insulin, tiotropium, albuterol. Active comorbidities include decompensated heart failure, COPD, and diabetes mellitus.

OBJECTIVE:
Overnight oxygen saturation dropped to 88% on multiple occasions — possible CPAP non-adherence or need for setting adjustment. BNP 2400 (prior day). Troponin negative. Echocardiogram demonstrates severely reduced ejection fraction of 25%. Bilateral lower extremity edema improving but persistent. Vital signs not fully documented in this note. Daily weight not recorded. Repeat BMP and BNP not yet resulted.

ASSESSMENT:
Decompensated systolic heart failure (EF 25%) with partial response to IV diuresis — 1.5L urine output overnight with mild symptomatic improvement and edema reduction. Nocturnal hypoxemia with O2 saturation 88% warrants CPAP optimization and consideration of supplemental oxygen titration. BNP remains significantly elevated. COPD co-management ongoing with bronchodilator therapy. Diabetes managed with insulin. Volume status improving but not yet at euvolemia.

PLAN:
Continue IV furosemide — reassess dose based on today's urine output and clinical examination. Daily weight and strict intake-output monitoring. Repeat BMP to assess electrolytes and renal function given diuresis. Repeat BNP in 48 hours to trend response. CPAP settings review — respiratory therapy consultation for titration; consider supplemental O2 if nocturnal hypoxemia persists. Continue carvedilol at current dose — hold if hemodynamics worsen. Continue tiotropium and albuterol for COPD. Insulin regimen adjusted per glucose logs. If EF does not improve, cardiology to discuss advanced heart failure therapies including ICD, CRT, or transplant evaluation. Cardiology and pulmonology active on case."""
    },
    {
        "conversation_id": "TCMSkaDOazcc",
        "sample_name": "Pneumonia - Discharge Summary",
        "category": "COMPLEX",
        "complexity_score": 96.4,
        "description": "Discharge summary for hospitalized patient with severe pneumonia and multiple comorbidities.",
        "conversation": """CLINICIAN: Let's review your hospital course before discharge. You came in with severe pneumonia.
PATIENT: Yes, I couldn't breathe and had a high fever.
CLINICIAN: Your chest X-ray showed consolidation in the right lower lobe. We started IV antibiotics.
PATIENT: The breathing got better after a few days.
CLINICIAN: Your cultures grew Streptococcus pneumoniae. We de-escalated to oral amoxicillin.
PATIENT: My diabetes was hard to control while I was sick.
CLINICIAN: Yes, your blood sugars were running high — we used an insulin drip initially.
PATIENT: And my kidneys?
CLINICIAN: You had acute kidney injury likely from the infection and dehydration. Creatinine peaked at 2.1 but came down to 1.4 at discharge.
PATIENT: What about my heart? The doctors were concerned.
CLINICIAN: You had atrial fibrillation during your stay — likely stress-induced. We started you on metoprolol and your heart rate is controlled.
PATIENT: I also have COPD. Was that affected?
CLINICIAN: Your COPD did flare during admission. We gave you steroids and nebulizers. You're going home on a prednisone taper.
PATIENT: That's a lot to manage at home.
CLINICIAN: We'll send you home with close follow-up. Continue amoxicillin, metoprolol, prednisone taper, insulin, and your inhalers.""",
        "soap_note": """SUBJECTIVE:
Discharge summary. Patient presented with severe community-acquired pneumonia with chief complaints of dyspnea and high fever. Hospital course notable for right lower lobe consolidation on chest X-ray, positive blood cultures growing Streptococcus pneumoniae, hyperglycemia requiring insulin drip with background diabetes mellitus, acute kidney injury with creatinine peak of 2.1 with partial recovery to 1.4 at discharge, new-onset atrial fibrillation attributed to physiologic stress, and COPD exacerbation managed with systemic corticosteroids and bronchodilators. Clinical improvement achieved with antibiotic de-escalation to oral amoxicillin.

OBJECTIVE:
Chest X-ray: right lower lobe consolidation on admission. Blood cultures: Streptococcus pneumoniae isolated. Creatinine peak 2.1, discharge value 1.4. Atrial fibrillation identified during admission — rate controlled with metoprolol at discharge. Blood glucose elevated during admission requiring insulin drip — improved with antibiotic therapy. COPD exacerbation treated with systemic steroids and nebulized bronchodilators. Discharge vital signs not documented in this summary.

ASSESSMENT:
Streptococcal community-acquired pneumonia with multi-system complications during hospitalization: acute kidney injury (resolved partially), new atrial fibrillation (rate controlled), COPD exacerbation (improving on steroid taper), and diabetic hyperglycemia (improved). Patient clinically improved and meeting discharge criteria with creatinine trending down and respiratory status stable.

PLAN:
Discharge medications: amoxicillin to complete antibiotic course, metoprolol for atrial fibrillation rate control, prednisone taper over 5 days for COPD, insulin regimen adjusted for home use, home inhalers resumed. Follow-up: primary care in 1 week, pulmonology for COPD management, cardiology for new atrial fibrillation (anticoagulation discussion pending), nephrology referral if creatinine does not continue to improve. Repeat chest X-ray in 6-8 weeks to confirm pneumonia resolution. Pneumococcal vaccination review — administer if not current. Patient and caregiver education on medication schedule, activity restrictions, and return precautions."""
    },

    # ── RARE / EDGE ──────────────────────────────────────────────────────────
    {
        "conversation_id": "qbvbY8tgvuDW",
        "sample_name": "Not Feeling Well - ER Visit",
        "category": "COMPLEX",
        "complexity_score": 100,
        "description": "ER visit with vague multi-system complaints and extensive workup in elderly patient.",
        "conversation": """CLINICIAN: What brings you to the ER today?
PATIENT: I just don't feel well. Everything feels off. I'm 78 years old and something isn't right.
CLINICIAN: Can you be more specific? Any pain, fever, trouble breathing?
PATIENT: Some nausea. Very fatigued. A little confused — my daughter noticed.
CLINICIAN: How long?
PATIENT: A few days of not feeling right. The confusion is new today.
CLINICIAN: Any falls or head injury?
PATIENT: No falls. No injury.
CLINICIAN: What medical conditions do you have?
PATIENT: Heart failure, diabetes, kidney disease, hypertension, atrial fibrillation. I'm on warfarin, insulin, metformin, lisinopril, and digoxin.
CLINICIAN: Any recent medication changes or missed doses?
PATIENT: My daughter thinks I missed a few doses of my medications.
CLINICIAN: Let me examine you and we'll get some urgent labs.
[Examination and labs performed]
CLINICIAN: Your INR is 5.8 — your blood is too thin. Digoxin level is elevated at 2.8. Sodium is low at 128. These are all contributing to how you feel.
PATIENT: That sounds serious.
CLINICIAN: Yes, we need to admit you and address these abnormalities carefully.""",
        "soap_note": """SUBJECTIVE:
A 78-year-old patient presents to the emergency department with several days of generalized malaise and acute-onset confusion noted by daughter on day of presentation. Associated nausea and severe fatigue. Denies falls, head trauma, focal neurological complaints, chest pain, and dyspnea. Significant past medical history: congestive heart failure, diabetes mellitus, chronic kidney disease, hypertension, and atrial fibrillation. Current medications: warfarin, insulin, metformin, lisinopril, and digoxin. Daughter reports probable missed medication doses over recent days.

OBJECTIVE:
Critical laboratory values: INR 5.8 (supratherapeutic — warfarin toxicity), digoxin level 2.8 ng/mL (elevated — digoxin toxicity), serum sodium 128 mEq/L (hyponatremia). Additional laboratory and vital sign findings not detailed in this note. Mental status examination reveals acute confusion confirmed by collateral history from daughter. Physical examination not fully documented.

ASSESSMENT:
Multi-factorial acute presentation in a complex elderly patient with polypharmacy: supratherapeutic anticoagulation (INR 5.8) with bleeding risk, digoxin toxicity (level 2.8) likely contributing to nausea, fatigue, and confusion, and hyponatremia (sodium 128) contributing to altered mental status. Probable medication non-adherence and/or altered drug clearance in the setting of chronic kidney disease as precipitating factors. Each abnormality requires careful correction given the patient's multiple comorbidities and drug interactions.

PLAN:
Hospital admission to monitored bed. Warfarin management: hold warfarin, consider vitamin K administration based on bleeding risk assessment; recheck INR in 12-24 hours. Digoxin toxicity: hold digoxin, continuous cardiac monitoring for digoxin-related arrhythmias, digoxin-specific antibody fragments (Digibind) if hemodynamic instability or life-threatening arrhythmia. Hyponatremia: determine etiology (SIADH vs. heart failure vs. diuretic effect), cautious sodium correction to avoid osmotic demyelination. Renal function monitoring given CKD and held nephrotoxic medications. Insulin dose adjustment during acute illness. Medication reconciliation and patient/caregiver education on medication adherence. Social work involvement for medication management support at home."""
    },
    {
        "conversation_id": "HMwd9FKxndyx",
        "sample_name": "Normal ROS Template",
        "category": "COMPLEX",
        "complexity_score": 100,
        "description": "Exhaustive review of systems template with every organ system documented.",
        "conversation": """CLINICIAN: I'm going to do a complete head-to-toe review of systems. Please answer yes or no and describe if yes.
PATIENT: Okay, ready.
CLINICIAN: Constitutional: fever, chills, weight changes, fatigue, night sweats?
PATIENT: Fatigue yes. Night sweats yes, for 2 months. No fever, no weight change, no chills.
CLINICIAN: Eyes: changes in vision, double vision, eye pain, redness?
PATIENT: Blurry vision sometimes. No double vision or pain.
CLINICIAN: Ears: hearing loss, ringing, ear pain, discharge?
PATIENT: Some ringing in my right ear.
CLINICIAN: Nose and throat: congestion, nosebleeds, sore throat, difficulty swallowing?
PATIENT: Sinus congestion. Occasional nosebleeds. No sore throat or swallowing problems.
CLINICIAN: Cardiovascular: chest pain, palpitations, swelling, shortness of breath at rest?
PATIENT: Palpitations sometimes. Occasional ankle swelling. No chest pain or rest dyspnea.
CLINICIAN: Respiratory: cough, wheeze, shortness of breath with exertion, hemoptysis?
PATIENT: Cough in the morning. Shortness of breath walking uphill. No blood.
CLINICIAN: Gastrointestinal: nausea, vomiting, diarrhea, constipation, blood in stool, heartburn?
PATIENT: Heartburn. Diarrhea a few times per week. No blood, no vomiting.
CLINICIAN: Genitourinary: frequency, urgency, burning, blood in urine?
PATIENT: Frequency and some urgency. No pain or blood.
CLINICIAN: Musculoskeletal: joint pain, muscle weakness, back pain, stiffness?
PATIENT: Lower back pain. Both knee pain. Morning stiffness about 30 minutes.
CLINICIAN: Neurological: headaches, dizziness, weakness, numbness, seizures, memory?
PATIENT: Headaches twice weekly. Dizziness when standing. Numbness in feet. Memory is worse.
CLINICIAN: Psychiatric: depression, anxiety, sleep problems, mood changes?
PATIENT: Mild depression. Anxious often. Sleep disrupted — waking at night.
CLINICIAN: Endocrine: heat or cold intolerance, excessive thirst, increased urination?
PATIENT: Cold intolerance. Polydipsia and polyuria.
CLINICIAN: Hematologic: bleeding, bruising, lymph node swelling?
PATIENT: Easy bruising. A lymph node in my neck.
CLINICIAN: Skin: rashes, changes, new lesions?
PATIENT: Dry skin and a new mole on my back my wife noticed.""",
        "soap_note": """SUBJECTIVE:
Comprehensive review of systems with multi-system involvement documented. Constitutional: fatigue and night sweats for 2 months; denies fever, chills, weight change. Ocular: intermittent blurry vision; denies diplopia or ocular pain. Auditory: right-sided tinnitus. Upper respiratory: chronic sinus congestion, episodic epistaxis; denies dysphagia. Cardiovascular: palpitations, intermittent bilateral ankle edema; denies chest pain or rest dyspnea. Pulmonary: morning cough, exertional dyspnea on inclines; denies hemoptysis or wheezing. Gastrointestinal: gastroesophageal reflux, intermittent diarrhea several times weekly; denies hematochezia or emesis. Genitourinary: urinary frequency and urgency without dysuria or hematuria. Musculoskeletal: lower back pain, bilateral knee pain, morning stiffness approximately 30 minutes. Neurological: twice-weekly headaches, orthostatic dizziness, bilateral foot paresthesias, cognitive decline. Psychiatric: mild depression, generalized anxiety, sleep fragmentation. Endocrine: cold intolerance, polydipsia, polyuria. Hematologic: easy bruising, cervical lymphadenopathy. Dermatologic: xerosis, new pigmented back lesion noted by spouse.

OBJECTIVE:
Full physical examination not documented in this review of systems encounter. Vital signs not recorded. Targeted examination findings not detailed.

ASSESSMENT:
Extensive multi-system symptom inventory requiring systematic diagnostic evaluation. High-priority concerns: polydipsia/polyuria/cold intolerance (diabetes mellitus and hypothyroidism), bilateral foot paresthesias and fatigue (peripheral neuropathy), new skin lesion (melanoma must be excluded), cervical lymphadenopathy with night sweats (lymphoma workup required), easy bruising (coagulopathy or thrombocytopenia), orthostatic dizziness (autonomic dysfunction vs. dehydration), morning stiffness with polyarthralgia (inflammatory arthropathy).

PLAN:
Priority laboratory workup: CBC with differential, CMP, HbA1c, TSH, lipid panel, coagulation studies (PT/INR, PTT), ANA, rheumatoid factor, anti-CCP, LDH, uric acid. Imaging: CT neck/chest/abdomen for lymphadenopathy evaluation. Dermatology referral for new back lesion — excisional biopsy likely indicated. Neurology referral for peripheral neuropathy evaluation including EMG/nerve conduction studies. Gastroenterology consideration for persistent diarrhea. Ophthalmology for blurry vision. Psychiatry or primary care management of depression and anxiety. Structured follow-up plan with primary care coordination across all subspecialties."""
    },
    {
        "conversation_id": "0X6AyPbbHl7k",
        "sample_name": "Sleepiness - Consult",
        "category": "RARE/EDGE",
        "complexity_score": 100,
        "description": "Neurology consult for excessive daytime sleepiness with suspected narcolepsy vs. idiopathic hypersomnia.",
        "conversation": """CLINICIAN: You've been referred for excessive daytime sleepiness. Tell me about it.
PATIENT: I fall asleep everywhere. At work, at dinner, while talking to people. I can't control it.
CLINICIAN: Do you fall asleep suddenly — like your muscles give out?
PATIENT: Yes! Sometimes when I laugh or get excited my knees buckle. I dropped a cup last week.
CLINICIAN: That's called cataplexy. Very important. Do you have sleep paralysis — wake up and can't move?
PATIENT: Yes, that happens. Very scary.
CLINICIAN: Hallucinations when falling asleep or waking up?
PATIENT: Yes — I see and hear things right before falling asleep. My doctor thought I was psychotic.
CLINICIAN: How long at night do you sleep?
PATIENT: 10 to 11 hours and still exhausted.
CLINICIAN: Any other medical conditions?
PATIENT: Thyroid problem — hypothyroidism. On levothyroxine. Also depression — on sertraline.
CLINICIAN: Any family history of similar symptoms?
PATIENT: My uncle had something similar — was never diagnosed.
CLINICIAN: This presentation is very consistent with narcolepsy type 1. The cataplexy is the key finding. We need a sleep study followed by an MSLT.
PATIENT: What is that?
CLINICIAN: A multiple sleep latency test — measures how fast you fall asleep during the day. It will confirm the diagnosis.
PATIENT: Will I need medication forever?
CLINICIAN: Likely yes, but many patients do very well on treatment.""",
        "soap_note": """SUBJECTIVE:
Patient presents to neurology for evaluation of severe excessive daytime sleepiness with inability to maintain wakefulness in social and occupational settings including at work and during conversations. Reports sudden loss of muscle tone triggered by emotional stimuli (laughing, excitement) with knee buckling and object dropping — consistent with cataplexy. Additional narcolepsy symptom tetrad features: sleep paralysis on waking (unable to move, frightening), and hypnagogic/hypnopompic hallucinations (visual and auditory) preceding sleep onset — previously misattributed to psychosis. Despite 10-11 hours of nightly sleep, non-restorative and exhaustion persists. Known comorbidities: hypothyroidism on levothyroxine, depression on sertraline. Family history positive for undiagnosed similar condition in paternal uncle.

OBJECTIVE:
Neurological examination not detailed in this note. Epworth Sleepiness Scale score not documented. Thyroid function tests not available at this visit. Current medications: levothyroxine, sertraline. Polysomnography and MSLT not yet performed — ordered at this visit.

ASSESSMENT:
Clinical presentation highly consistent with Narcolepsy Type 1 (narcolepsy with cataplexy) based on the presence of all four classic tetrad features: excessive daytime sleepiness, cataplexy with emotional triggers, sleep paralysis, and hypnagogic/hypnopompic hallucinations. Family history adds further support. Hypothyroidism as contributing cause of fatigue must be confirmed as adequately treated. Sertraline may modestly suppress REM and cataplexy symptoms — medication interaction consideration. Prior psychiatric misattribution of hallucinations highlights diagnostic complexity of narcolepsy.

PLAN:
Overnight polysomnography followed by multiple sleep latency test (MSLT) to confirm narcolepsy diagnosis — REM sleep latency under 15 minutes on PSG and mean sleep latency under 8 minutes with two or more sleep onset REM periods on MSLT expected. CSF hypocretin/orexin level measurement to be considered for definitive Type 1 confirmation. TSH to confirm adequate hypothyroid treatment. Anticipated pharmacotherapy: sodium oxybate (Xyrem) for cataplexy and nighttime sleep consolidation, modafinil or armodafinil for daytime alertness. Sertraline continuation discussed — may benefit cataplexy but interaction with planned medications to be reviewed. Patient counseled on driving restrictions until diagnosis confirmed and treatment stabilized. Occupational impact discussed. Follow-up in 2-4 weeks after sleep study completion."""
    }
]


def build_demo_data():
    """Build complete demo_data.json with attribution run on each case"""
    print(f"Building demo data for {len(CASES)} cases...")
    demo_cases = []

    for i, case in enumerate(CASES):
        print(f"  [{i+1}/{len(CASES)}] {case['sample_name']} ({case['category']})...")

        # Run real attribution logic
        attr_result = attribute_sources(
            soap_note=case["soap_note"],
            conversation=case["conversation"]
        )

        if attr_result["success"]:
            stats = attr_result["data"]["statistics"]
            attributions = attr_result["data"]["attributions"]
        else:
            print(f"    ⚠ Attribution failed: {attr_result['error']}")
            stats = {
                "total_entities": 0, "entities_attributed": 0,
                "hallucination_count": 0, "hallucination_rate": 0.0,
                "attribution_coverage": 0.0, "average_confidence": 0.0,
                "quality_score": "unknown"
            }
            attributions = []

        demo_cases.append({
            "conversation_id": case["conversation_id"],
            "sample_name": case["sample_name"],
            "category": case["category"],
            "complexity_score": case["complexity_score"],
            "description": case["description"],
            "conversation": case["conversation"],
            "soap_note": case["soap_note"],
            "attributions": attributions,
            "statistics": stats
        })

        print(f"    ✓ {stats['total_entities']} entities, "
              f"{stats['hallucination_count']} hallucinations, "
              f"coverage {stats.get('attribution_coverage', 0):.1%}, "
              f"quality {stats['quality_score'].upper()}")

    output = {
        "metadata": {
            "total_cases": len(demo_cases),
            "categories": {
                "SIMPLE": sum(1 for c in demo_cases if c["category"] == "SIMPLE"),
                "MODERATE": sum(1 for c in demo_cases if c["category"] == "MODERATE"),
                "COMPLEX": sum(1 for c in demo_cases if c["category"] == "COMPLEX"),
                "RARE/EDGE": sum(1 for c in demo_cases if c["category"] == "RARE/EDGE"),
            },
            "description": "Pre-generated demo data for Ambient Documentation portfolio demo"
        },
        "cases": demo_cases
    }

    with open("/home/claude/demo_data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ demo_data.json written with {len(demo_cases)} cases")
    return output


if __name__ == "__main__":
    build_demo_data()
EOF
