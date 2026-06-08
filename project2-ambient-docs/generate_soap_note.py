#!/usr/bin/env python3
"""
Ambient Transcript API - Generate SOAP notes from conversations

This API takes a patient-clinician conversation and generates a structured
SOAP note using Claude API.

Input: conversation (text)
Output: SOAP note (text)

Features:
- Clean separation of system and user prompts
- Error handling and validation
- Proper database integration
- Type hints for clarity
- Comprehensive logging
"""

import json
from sre_parse import ANY
import psycopg2
import psycopg2.extras
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional
import anthropic
import os
import sys
import logging
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": "health_ai_portfolio",
    "host": "localhost"
}

# Claude configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 1500
CLAUDE_TEMPERATURE = 0

# ============================================================================
# PROMPTS
# ============================================================================

SYSTEM_PROMPT = """You are an expert medical documentation specialist with 20+ years of clinical experience.

Your task: Generate accurate, complete SOAP notes from patient-clinician conversations for medical records.

SOAP STRUCTURE:

SUBJECTIVE:
- Chief complaint and history of present illness
- Associated symptoms and their duration/severity
- Relevant past medical history and medications
- Minimum 50 words

OBJECTIVE:
- Vital signs (if documented)
- Physical examination findings
- Any lab or diagnostic results mentioned
- Minimum 50 words

ASSESSMENT:
- Clinical impressions and diagnoses
- Clinical reasoning and justification
- Differential considerations if relevant
- Minimum 50 words

PLAN:
- Diagnostic tests or procedures ordered
- Medications prescribed or recommended
- Patient education and lifestyle modifications
- Follow-up and referrals
- Minimum 50 words

Total length: 300-500 words

QUALITY STANDARDS:
- Medically accurate and relevant
- Clinically sound
- Complete yet concise
- Professional medical language
- Logical progression S→O→A→P

CRITICAL RULES - DO NOT VIOLATE:
1. NEVER invent or hallucinate clinical information
2. ONLY use information present in the conversation
3. If data is missing, note "not documented" rather than inventing
4. Maintain accuracy in all clinical details
5. Use proper medical terminology
6. Be objective and factual

Generate the SOAP note now."""


def build_user_prompt(conversation: str) -> str:
    """
    Build the user prompt for SOAP generation.
    
    Args:
        conversation: The patient-clinician conversation text
    
    Returns:
        The user prompt string
    """
    return f"""Generate a SOAP note from the following patient-clinician conversation:

{conversation}

Return ONLY the SOAP note in the four-section format specified in system instructions.
Do not add any preamble, explanation, or additional text.
Note: If conversation is brief, it's acceptable to have shorter SOAP sections,
but maintain the four-section structure."""


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

class DatabaseError(Exception):
    """Database operation error"""
    pass


def get_db_connection():
    """
    Get PostgreSQL database connection.
    
    Returns:
        psycopg2 connection object
    
    Raises:
        DatabaseError: If connection fails
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        raise DatabaseError(f"Failed to connect to database: {e}")


def get_conversation_from_db(conv_id: str, conn) -> str:
    """
    Fetch conversation text from database.
    
    Args:
        conv_id: Conversation ID (primary key)
        conn: Database connection
    
    Returns:
        Complete conversation text (string)
    
    Raises:
        DatabaseError: If query fails or conversation not found
    """
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT conversation
            FROM conversations
            WHERE id = %s
        """, (conv_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if row is None:
            raise DatabaseError(f"Conversation not found: {conv_id}")
        
        # Extract string from the row
        # DictCursor returns dict-like object, access by column name
        conversation_text = row['conversation']
        
        if not conversation_text:
            raise DatabaseError(f"Conversation is empty: {conv_id}")
        
        logger.info(f"✓ Fetched conversation {conv_id} ({len(conversation_text)} chars)")
        return conversation_text
    
    except psycopg2.Error as e:
        raise DatabaseError(f"Database query error: {e}")


# ============================================================================
# CLAUDE API OPERATIONS
# ============================================================================

class ClaudeAPIError(Exception):
    """Claude API error"""
    pass


def generate_soap_note(conversation: str) -> str:
    """
    Generate SOAP note from conversation using Claude API.
    
    Args:
        conversation: Patient-clinician conversation text
    
    Returns:
        SOAP note text
    
    Raises:
        ClaudeAPIError: If API call fails
        ValueError: If input validation fails
    """
    # Validate input
    if not conversation or len(conversation.strip()) < 50:
        raise ValueError("Conversation too short (minimum 50 characters)")
    
    try:
        logger.info(f"→ Calling Claude API... ({len(conversation)} char input)")
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        user_prompt = build_user_prompt(conversation)
        
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract text from response
        soap_note = response.content[0].text.strip()
        
        # Remove markdown code blocks if present
        if soap_note.startswith("```"):
            # Remove opening ```
            soap_note = soap_note.split("\n", 1)[1]
            # Remove closing ```
            soap_note = soap_note.rsplit("```", 1)[0]
            soap_note = soap_note.strip()
        
        logger.info(f"✓ Generated SOAP note ({len(soap_note)} chars)")
        return soap_note
    
    except anthropic.APIError as e:
        raise ClaudeAPIError(f"Claude API error: {e}")
    except Exception as e:
        raise ClaudeAPIError(f"Unexpected error calling Claude API: {e}")


def get_soap_note(conversation: str) -> Dict:
#def generate_soap_note(conversation: str) -> str:
#def generate_soap_from_conversation(conv_id: str) -> Dict:
    """
    Main API function: Generate SOAP note from conversation text passed.

    Args:
        conv_id: Conversation text

    Returns:
        Dict with:
        - success (bool): Whether generation succeeded
        - soap_note (str): Generated SOAP note (if successful)
        - error (str): Error message (if failed)
        - metadata (dict): Additional info (chars, model, timestamp)
    """
    result = {
        "success": False,
        "soap_note": None,
        "error": None,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": CLAUDE_MODEL
        }
    }

    try:
        logger.info(f"→ Calling Claude API... ({len(conversation)} char input)")
        
        # Validate input
        if not conversation or len(conversation.strip()) < 50:
            raise ValueError("Conversation too short (minimum 50 characters)")

        # Generate SOAP note
        soap_note = generate_soap_note(conversation)
        result["metadata"]["output_chars"] = len(soap_note)

        # Validate SOAP note
        is_valid, validation_msg = validate_soap_note(soap_note)
        result["metadata"]["validation"] = validation_msg

        if not is_valid:
            result["error"] = f"SOAP validation failed: {validation_msg}"
            logger.warning(f"✗ Validation failed: {validation_msg}")
            return result

        # Success!
        result["success"] = True
        result["soap_note"] = soap_note
        logger.info(f"✓ SUCCESS: SOAP note generated ({len(soap_note)} chars)")

    except ClaudeAPIError as e:
        result["error"] = f"API_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")

    except ValueError as e:
        result["error"] = f"VALIDATION_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")

    except Exception as e:
        result["error"] = f"UNEXPECTED_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")

    return result





# ============================================================================
# VALIDATION
# ============================================================================

def validate_soap_note(soap_note: str) -> Tuple[bool, str]:
    """
    Validate that SOAP note meets minimum requirements.
    
    Args:
        soap_note: The generated SOAP note
    
    Returns:
        Tuple of (is_valid, message)
    """
    issues = []
    
    # Check length
    if len(soap_note) < 200:
        issues.append(f"Too short ({len(soap_note)} < 200 chars)")
    
    # Check for required sections
    required_sections = ['SUBJECTIVE', 'OBJECTIVE', 'ASSESSMENT', 'PLAN']
    missing = [s for s in required_sections if s not in soap_note.upper()]
    if missing:
        issues.append(f"Missing sections: {', '.join(missing)}")
    
    if issues:
        return False, "; ".join(issues)
    
    return True, "Valid"


# ============================================================================
# MAIN API FUNCTION
# ============================================================================

def generate_soap_from_conversation(conv_id: str) -> Dict:
    """
    Main API function: Generate SOAP note from conversation in database.
    
    Args:
        conv_id: Conversation ID to process
    
    Returns:
        Dict with:
        - success (bool): Whether generation succeeded
        - soap_note (str): Generated SOAP note (if successful)
        - error (str): Error message (if failed)
        - metadata (dict): Additional info (chars, model, timestamp)
    """
    result = {
        "success": False,
        "soap_note": None,
        "error": None,
        "metadata": {
            "conv_id": conv_id,
            "timestamp": datetime.now().isoformat(),
            "model": CLAUDE_MODEL
        }
    }
    
    conn = None
    
    try:
        # Connect to database
        conn = get_db_connection()
        logger.info(f"[API] Processing conversation: {conv_id}")
        
        # Fetch conversation from database
        conversation = get_conversation_from_db(conv_id, conn)
        result["metadata"]["input_chars"] = len(conversation)
        
        # Generate SOAP note
        soap_note = generate_soap_note(conversation)
        result["metadata"]["output_chars"] = len(soap_note)
        
        # Validate SOAP note
        is_valid, validation_msg = validate_soap_note(soap_note)
        result["metadata"]["validation"] = validation_msg
        
        if not is_valid:
            result["error"] = f"SOAP validation failed: {validation_msg}"
            logger.warning(f"✗ Validation failed: {validation_msg}")
            return result
        
        # Success!
        result["success"] = True
        result["soap_note"] = soap_note
        logger.info(f"✓ SUCCESS: SOAP note generated ({len(soap_note)} chars)")
        
    except DatabaseError as e:
        result["error"] = f"DATABASE_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")
    
    except ClaudeAPIError as e:
        result["error"] = f"API_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")
    
    except ValueError as e:
        result["error"] = f"VALIDATION_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")
    
    except Exception as e:
        result["error"] = f"UNEXPECTED_ERROR: {str(e)}"
        logger.error(f"✗ {result['error']}")
    
    finally:
        if conn:
            conn.close()
    
    return result


# ============================================================================
# CLI & TESTING
# ============================================================================

def get_all_conversations():
    """
    CLI interface for getting conversations for testing

    Usage:
        python get_all_conversations
    """

    eval_convs = ["0U15DA7ozgp2",
"CN4XhgsJj8UU",
"S0hRoqZCct2O",
"u7qOicVQWbsj",
"B3YKBkDgcBnT",
"CEDgXx9DgFbC",
"Y9BsOifbX6cR",
"bLiHoeCVVrjp",
"Ixe2I3lrKFYK",
"Xs4GRIFhjHJT",
"2qeiMvG87y1M",
"Win8pvy0nQpc",
"Chp9WGwltx0p",
"q5dVhK86R6je",
"OJJLdMsb4iqO",
"C1ymAgLDI2nF",
"TCMSkaDOazcc",
"qbvbY8tgvuDW",
"HMwd9FKxndyx",
"0X6AyPbbHl7k"
]

    conn = None
    logger.info(f"Extracting conversations ")

    try:
        # Connect to database
        conn = get_db_connection()
 
        for idx, conv_id in enumerate [ANY] (eval_convs, 1):
            #logger.info(f"[API] Processing conversation #{idx}: {conv_id}")
            print(f"conversation id #{idx}: {conv_id}")
            conv_text = get_conversation_from_db(conv_id, conn)
            print(f"{conv_text}")
    
        logger.info(f"End Extracting conversations ")
    
    finally:
        if conn:
            conn.close()
    
    return 1



def main():
    """
    CLI interface for testing the API.
    
    Usage:
        python3 get_soap_note.py [conversation_id]
    
    Example:
        python3 get_soap_note.py 0U15DA7ozgp2
    """
    # Get conversation ID from command line or use default for testing
    if len(sys.argv) > 1:
        conv_id = sys.argv[1]
    else:
        # Default for testing
        conv_id = '0U15DA7ozgp2'
        logger.info(f"No conversation ID provided, using default: {conv_id}")
    
    # Call the API
    result = generate_soap_from_conversation(conv_id)
    
    # Print results
    print("\n" + "="*70)
    print(f"CONVERSATION ID: {result['metadata']['conv_id']}")
    print(f"SUCCESS: {result['success']}")
    print("="*70)
    
    if result['success']:
        print(f"\nSOAP NOTE:\n{result['soap_note']}")
        print("\n" + "-"*70)
        print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
    else:
        print(f"\nERROR: {result['error']}")
        print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
    
    return 0 if result['success'] else 1



if __name__ == "__main__":
    sys.exit(main())
