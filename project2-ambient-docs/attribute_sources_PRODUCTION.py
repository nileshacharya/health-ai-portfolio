#!/usr/bin/env python3
"""
Ambient Documentation - Level 1 Source Attribution API

Attributes clinical entities from SOAP notes to conversation sources.
Simple, reliable, production-ready implementation.

Usage:
    result = attribute_sources(soap_note, conversation)
    if result['success']:
        for attr in result['data']['attributions']:
            print(f"{attr['soap_text']} ← {attr['source_text']}")
"""

import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Thresholds and scoring
FUZZY_THRESHOLD = 0.80
HALLUCINATION_THRESHOLD = 0.70
GOOD_CONFIDENCE_THRESHOLD = 0.75

# Match confidence scores
EXACT_MATCH_CONFIDENCE = 0.95
CASE_INSENSITIVE_CONFIDENCE = 0.90
FUZZY_MATCH_CONFIDENCE_BASE = 0.80
PARTIAL_MATCH_CONFIDENCE = 0.75
WEAK_MATCH_CONFIDENCE = 0.50

# Medical keywords database
MEDICAL_KEYWORDS = {
    'diagnoses': [
        'diabetes', 'hypertension', 'asthma', 'pneumonia', 'bronchitis', 'copd',
        'heart disease', 'coronary', 'myocardial infarction', 'arrhythmia', 'heart failure',
        'stroke', 'cancer', 'leukemia', 'lymphoma', 'arthritis', 'osteoporosis',
        'kidney disease', 'renal', 'liver disease', 'cirrhosis', 'hepatitis',
        'thyroid', 'hyperthyroid', 'hypothyroid', 'anemia', 'infection', 'sepsis',
        'flu', 'covid', 'tuberculosis', 'hiv', 'aids',
        'depression', 'anxiety', 'schizophrenia', 'bipolar', 'autism', 'adhd',
        'gastroenteritis', 'ulcer', 'ibs', 'crohn\'s', 'colitis', 'migraine'
    ],
    'symptoms': [
        'pain', 'ache', 'fever', 'cough', 'shortness of breath', 'dyspnea',
        'nausea', 'vomiting', 'diarrhea', 'fatigue', 'weakness', 'dizziness',
        'headache', 'chest pain', 'abdominal pain', 'rash', 'itching', 'swelling',
        'bleeding', 'bruising', 'difficulty swallowing', 'hoarseness', 'wheezing',
        'congestion', 'discharge', 'tremor', 'numbness', 'tingling', 'memory loss',
        'confusion', 'sleep disturbance', 'weight loss'
    ],
    'medications': [
        'aspirin', 'ibuprofen', 'acetaminophen', 'metformin', 'insulin', 'lisinopril',
        'atorvastatin', 'amoxicillin', 'penicillin', 'warfarin', 'heparin', 'morphine',
        'oxycodone', 'hydrocodone', 'lorazepam', 'alprazolam', 'sertraline', 'fluoxetine',
        'omeprazole', 'metoprolol', 'calcium', 'vitamin', 'antibiotic', 'steroid',
        'hormone', 'anticoagulant', 'antihypertensive'
    ],
    'vitals': [
        'temperature', 'temp', 'afebrile', 'blood pressure', 'bp', 'heart rate', 'hr',
        'pulse', 'respiratory rate', 'rr', 'respiration', 'oxygen saturation', 'spo2',
        'o2 sat', 'pulse oximetry', 'weight', 'height', 'bmi', 'body mass index'
    ],
    'procedures': [
        'x-ray', 'mri', 'ct scan', 'ultrasound', 'endoscopy', 'colonoscopy',
        'surgery', 'operation', 'biopsy', 'aspiration', 'injection', 'catheter',
        'intubation', 'ventilation', 'dialysis', 'transfusion', 'transplant',
        'bypass', 'angioplasty', 'stent', 'ablation'
    ]
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

def extract_entities(soap_note: str) -> List[Dict]:
    """
    Extract medical entities from SOAP note.
    
    Args:
        soap_note (str): SOAP note text
        
    Returns:
        list: Entities with type, deduped
        
    Example:
        >>> extract_entities("Patient has fever and pneumonia")
        [{'text': 'fever', 'type': 'symptoms'}, {'text': 'pneumonia', 'type': 'diagnoses'}]
    """
    entities = []
    seen = set()
    
    for entity_type, keywords in MEDICAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in soap_note.lower():
                # Skip duplicates (case-insensitive)
                keyword_lower = keyword.lower()
                if keyword_lower not in seen:
                    seen.add(keyword_lower)
                    entities.append({
                        'text': keyword,
                        'type': entity_type,
                    })
    
    logger.debug(f"Extracted {len(entities)} unique entities from SOAP note")
    return entities

# ============================================================================
# SOURCE FINDING
# ============================================================================

def find_source_exact(entity_text: str, conversation: str) -> Optional[Dict]:
    """
    Find entity source using exact string matching.
    
    Args:
        entity_text (str): Entity to search for
        conversation (str): Conversation text
        
    Returns:
        dict: Source info if found, None otherwise
    """
    lines = conversation.split('\n')
    
    for line_num, line in enumerate(lines):
        if entity_text.lower() in line.lower():
            return {
                'found': True,
                'source_text': line.strip(),
                'source_line': line_num,
                'method': 'exact',
                'confidence': EXACT_MATCH_CONFIDENCE if entity_text in line 
                              else CASE_INSENSITIVE_CONFIDENCE
            }
    
    return None


def find_source_fuzzy(entity_text: str, conversation: str, 
                     threshold: float = FUZZY_THRESHOLD) -> Optional[Dict]:
    """
    Find entity source using fuzzy string matching.
    
    Args:
        entity_text (str): Entity to search for
        conversation (str): Conversation text
        threshold (float): Similarity threshold (0.0-1.0)
        
    Returns:
        dict: Source info if found, None otherwise
    """
    lines = conversation.split('\n')
    best_match = None
    best_ratio = 0.0
    
    for line_num, line in enumerate(lines):
        line_clean = line.lower().strip()
        entity_clean = entity_text.lower().strip()
        
        ratio = SequenceMatcher(None, entity_clean, line_clean).ratio()
        
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = (line_num, line.strip(), ratio)
    
    if best_ratio > threshold:
        return {
            'found': True,
            'source_text': best_match[1],
            'source_line': best_match[0],
            'method': 'fuzzy',
            'confidence': best_match[2]
        }
    
    return None


def find_source(entity_text: str, conversation: str, 
               use_fuzzy: bool = True) -> Optional[Dict]:
    """
    Find entity source (try exact first, then fuzzy).
    
    Args:
        entity_text (str): Entity to search for
        conversation (str): Conversation text
        use_fuzzy (bool): Whether to try fuzzy matching fallback
        
    Returns:
        dict: Source info if found, None otherwise
    """
    # Try exact match first (fast)
    result = find_source_exact(entity_text, conversation)
    if result:
        return result
    
    # Try fuzzy match (slower, only if exact failed)
    if use_fuzzy:
        result = find_source_fuzzy(entity_text, conversation)
        if result:
            return result
    
    return None

# ============================================================================
# CONFIDENCE AND HALLUCINATION DETECTION
# ============================================================================

def calculate_confidence(source_method: str, match_similarity: float = 1.0) -> float:
    """
    Calculate confidence score based on matching method.
    
    Args:
        source_method (str): 'exact', 'fuzzy', 'partial', 'weak', or 'none'
        match_similarity (float): Similarity ratio if fuzzy (0.0-1.0)
        
    Returns:
        float: Confidence score (0.0-1.0)
    """
    if source_method == 'exact':
        return EXACT_MATCH_CONFIDENCE
    elif source_method == 'fuzzy':
        # Scale fuzzy confidence by similarity
        return FUZZY_MATCH_CONFIDENCE_BASE * match_similarity
    elif source_method == 'partial':
        return PARTIAL_MATCH_CONFIDENCE
    elif source_method == 'weak':
        return WEAK_MATCH_CONFIDENCE
    else:  # 'none' or unknown
        return 0.0


def detect_hallucination(confidence: float, 
                        threshold: float = HALLUCINATION_THRESHOLD) -> bool:
    """
    Detect if entity is likely hallucinated (not in conversation).
    
    Args:
        confidence (float): Confidence score (0.0-1.0)
        threshold (float): Confidence threshold below which is hallucination
        
    Returns:
        bool: True if likely hallucination, False otherwise
    """
    return confidence < threshold

# ============================================================================
# MAIN API
# ============================================================================

def attribute_sources(
    soap_note: str,
    conversation: str,
    soap_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    use_fuzzy: bool = True
) -> Dict:
    """
    Attribute clinical entities from SOAP note to conversation sources.
    
    This is the main API function that coordinates entity extraction,
    source finding, and hallucination detection.
    
    Args:
        soap_note (str): Generated SOAP note from LLM
        conversation (str): Original patient-clinician conversation
        soap_id (str, optional): ID of generated SOAP note (for database linking)
        conversation_id (str, optional): ID of conversation (for database linking)
        use_fuzzy (bool): Whether to use fuzzy matching for sources
        
    Returns:
        dict: {
            'success': bool,
            'data': {
                'attributions': [...],
                'statistics': {...}
            },
            'error': str or None
        }
        
    Example:
        >>> result = attribute_sources(soap_note, conversation)
        >>> if result['success']:
        ...     for attr in result['data']['attributions']:
        ...         print(f"{attr['soap_text']} ← {attr['source_text']}")
    """
    
    # Input validation
    if not soap_note or not isinstance(soap_note, str):
        logger.error("Invalid SOAP note: empty or not a string")
        return {
            'success': False,
            'data': None,
            'error': 'Invalid SOAP note: must be non-empty string',
            'timestamp': datetime.now().isoformat()
        }
    
    if not conversation or not isinstance(conversation, str):
        logger.error("Invalid conversation: empty or not a string")
        return {
            'success': False,
            'data': None,
            'error': 'Invalid conversation: must be non-empty string',
            'timestamp': datetime.now().isoformat()
        }
    
    try:
        logger.info(f"Starting attribution (soap_id={soap_id}, conv_id={conversation_id})")
        logger.debug(f"SOAP length: {len(soap_note)} chars, Conversation length: {len(conversation)} chars")
        
        # Extract entities
        entities = extract_entities(soap_note)
        logger.info(f"Extracted {len(entities)} entities")
        
        if not entities:
            logger.warning("No entities extracted from SOAP note")
            return {
                'success': False,
                'data': {
                    'attributions': [],
                    'statistics': {
                        'total_entities': 0,
                        'entities_attributed': 0,
                        'hallucination_count': 0,
                        'hallucination_rate': 0.0,
                        'average_confidence': 0.0,
                        'quality_score': 'none'
                    }
                },
                'error': 'No entities found in SOAP note',
                'timestamp': datetime.now().isoformat()
            }
        
        # Process each entity
        attributions = []
        hallucination_count = 0
        confidence_scores = []
        
        for entity in entities:
            logger.debug(f"Processing entity: {entity['text']} ({entity['type']})")
            
            # Find source
            source = find_source(entity['text'], conversation, use_fuzzy=use_fuzzy)
            
            if source:
                # Calculate confidence
                confidence = calculate_confidence(source['method'], 
                                                source.get('confidence', 1.0))
            else:
                # No source found
                confidence = 0.0
                source = {
                    'found': False,
                    'source_text': None,
                    'source_line': None,
                    'method': 'none'
                }
            
            # Detect hallucination
            is_hallucination = detect_hallucination(confidence)
            if is_hallucination:
                hallucination_count += 1
                logger.warning(f"Hallucination detected: {entity['text']} (confidence: {confidence})")
            
            confidence_scores.append(confidence)
            
            # Create attribution record
            attribution = {
                'soap_text': entity['text'],
                'entity_type': entity['type'],
                'source_text': source['source_text'],
                'source_line': source['source_line'],
                'confidence': round(confidence, 4),
                'is_hallucination': is_hallucination,
                'match_method': source['method']
            }
            
            # Add optional database IDs
            if soap_id:
                attribution['soap_id'] = soap_id
            if conversation_id:
                attribution['conversation_id'] = conversation_id
            
            attributions.append(attribution)
        
        # Calculate statistics
        total_entities = len(attributions)
        entities_attributed = sum(1 for a in attributions if not a['is_hallucination'])
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        hallucination_rate = hallucination_count / total_entities if total_entities > 0 else 0.0
        
        # Quality assessment
        if hallucination_rate == 0.0 and avg_confidence > 0.90:
            quality_score = 'excellent'
        elif hallucination_rate < 0.10 and avg_confidence > 0.80:
            quality_score = 'high'
        elif hallucination_rate < 0.25 and avg_confidence > 0.70:
            quality_score = 'medium'
        else:
            quality_score = 'low'
        
        statistics = {
            'total_entities': total_entities,
            'entities_attributed': entities_attributed,
            'entities_not_attributed': hallucination_count,
            'hallucination_count': hallucination_count,
            'hallucination_rate': round(hallucination_rate, 4),
            'attribution_coverage': round(entities_attributed / total_entities, 4) if total_entities > 0 else 0.0,
            'average_confidence': round(avg_confidence, 4),
            'quality_score': quality_score
        }
        
        logger.info(f"Attribution complete: {entities_attributed}/{total_entities} attributed, "
                   f"{hallucination_count} hallucinations, quality={quality_score}")
        
        return {
            'success': True,
            'data': {
                'attributions': attributions,
                'statistics': statistics
            },
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Attribution failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'data': None,
            'error': f'Attribution failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# UTILITIES
# ============================================================================

def format_for_display(result: Dict) -> str:
    """Format attribution result for display."""
    if not result['success']:
        return f"Error: {result['error']}"
    
    output = []
    output.append("=" * 70)
    output.append("SOURCE ATTRIBUTIONS")
    output.append("=" * 70)
    
    stats = result['data']['statistics']
    output.append(f"\nStatistics:")
    output.append(f"  Total entities: {stats['total_entities']}")
    output.append(f"  Attributed: {stats['entities_attributed']}")
    output.append(f"  Hallucinations: {stats['hallucination_count']}")
    output.append(f"  Coverage: {stats['attribution_coverage']:.1%}")
    output.append(f"  Avg confidence: {stats['average_confidence']:.2f}")
    output.append(f"  Quality: {stats['quality_score'].upper()}")
    output.append("")
    
    for attr in result['data']['attributions']:
        status = "⚠️ HALLUCINATION" if attr['is_hallucination'] else "✓"
        output.append(f"{status} {attr['soap_text']:<20} (conf: {attr['confidence']:.2f})")
        if attr['source_text']:
            output.append(f"   ← {attr['source_text']}")
        output.append("")
    
    return "\n".join(output)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Example usage
    #soap_note = "denies fever, productive cough, and dyspnea on exertion"
    #conversation = """PATIENT: I've been having a cough with sputum for 2 days. 
        #I have a don't have fever. 
        #When I climb stairs, I get short of breath."""

    soap_note = """
    **SUBJECTIVE:**
    Patient presents with a productive cough lasting approximately one week, producing yellow sputum. Fever began three days ago, reaching temperatures of 101-102°F. Patient reports mild chest tightness associated with forceful coughing episodes, but denies severe chest pain. Experiences mild dyspnea on exertion, specifically when climbing stairs. No other associated symptoms documented. Past medical history, current medications, and allergies not documented in this encounter.

    **OBJECTIVE:**
    Physical examination reveals abnormal lung sounds, particularly coarse or diminished breath sounds on the right side as noted by clinician during auscultation. Vital signs not specifically documented beyond patient-reported fever temperatures. Chest X-ray performed showing pulmonary infiltrates consistent with pneumonic process. Complete physical examination findings, including other vital signs, general appearance, and additional system examinations not documented in this conversation.

    **ASSESSMENT:**
    Clinical presentation consistent with community-acquired pneumonia based on constellation of symptoms including productive cough with purulent sputum, fever, mild dyspnea on exertion, abnormal lung examination findings, and radiographic evidence of pulmonary infiltrates on chest X-ray. The unilateral nature of abnormal lung sounds on the right side correlates with likely localized pneumonic process. Patient's symptom duration and fever pattern support acute bacterial pneumonia as primary diagnosis.

    **PLAN:**
    Chest X-ray completed showing infiltrates confirming pneumonia diagnosis. Specific antibiotic therapy, dosing, and duration not documented in this conversation. Patient education regarding diagnosis and expected course not documented. Follow-up instructions, return precautions, activity restrictions, and additional diagnostic testing such as complete blood count or blood cultures not mentioned. Referral needs and symptomatic treatment recommendations not documented in this encounter.
    """

    conversation = """
    PATIENT: I've been having a cough for about a week. It's pretty bad, 
    and I'm coughing up some yellow stuff.
    
    CLINICIAN: How long have you had the fever?
    
    PATIENT: The fever started about 3 days ago. It usually goes up to 
    around 101 or 102 degrees.
    
    CLINICIAN: Any chest pain or shortness of breath?
    
    PATIENT: My chest feels a little tight when I cough hard, but nothing 
    severe. I do get a bit short of breath when I climb stairs.
    
    CLINICIAN: Let me examine you and we'll get a chest X-ray.
    [Examination and stethoscope findings]
    
    CLINICIAN: Your lungs sound a bit rough, especially on the right side. 
    The X-ray shows some infiltrates. You likely have pneumonia.
    """

    #result = attribute_sources("cough", "patient I was coughing at night")
    result = attribute_sources(soap_note, conversation)
    print(format_for_display(result))
